#!/usr/bin/env python3
"""Compile exact Cairo decoder functions with guarded allocation fixtures.

Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: MIT
The supplied source must be a verified Cairo release or its patched copy.
This focused host check is not a complete Cairo package or target runtime test.
"""
import argparse
import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import xml.etree.ElementTree as ET


def extract(path, name):
    text = path.read_text()
    match = re.search(r'^' + re.escape(name) + r' \(', text, re.M)
    if match is None:
        raise ValueError(f'missing production function {name}: {path}')
    start = text.rfind('\n', 0, match.start() - 1) + 1
    end = text.index('\n}', match.end()) + 2
    line = text.count('\n', 0, start) + 1
    return f'#line {line} "{path.as_posix()}"\n' + text[start:end] + '\n'



def cppcheck(args, generated, compile_flags):
    """Analyze the unchanged GCC-preprocessed unit with its checked ABI."""
    output = args.output
    commands = []

    def gcc(extra):
        command = [args.cc, *compile_flags, *extra]
        commands.append(command)
        return subprocess.check_output(command, text=True)

    macros_text = gcc(['-dM', '-E', str(generated)])
    (output / 'gcc-macros.h').write_text(macros_text)
    macros = dict(re.findall(r'^#define (\w+) (.+)$', macros_text, re.M))
    sizes = {'bool': 1}
    for name, macro in [('short', 'SHORT'), ('int', 'INT'), ('long', 'LONG'),
                        ('long-long', 'LONG_LONG'), ('float', 'FLOAT'),
                        ('double', 'DOUBLE'), ('long-double', 'LONG_DOUBLE'),
                        ('pointer', 'POINTER'), ('size_t', 'SIZE_T'),
                        ('wchar_t', 'WCHAR_T')]:
        sizes[name] = int(macros[f'__SIZEOF_{macro}__'])
    char_bit = int(macros['__CHAR_BIT__'])
    unsigned_char = '__CHAR_UNSIGNED__' in macros
    platform = ET.Element('platform')
    ET.SubElement(platform, 'char_bit').text = str(char_bit)
    ET.SubElement(platform, 'default-sign').text = 'unsigned' if unsigned_char else 'signed'
    size_node = ET.SubElement(platform, 'sizeof')
    for name, value in sizes.items():
        ET.SubElement(size_node, name).text = str(value)
    platform_path = output / 'gcc-platform.xml'
    ET.ElementTree(platform).write(platform_path, encoding='utf-8', xml_declaration=True)

    # Check every XML value with the same compiler, including the bool size.
    assertions = ['#include <stddef.h>', '#include <limits.h>']
    for name, value in sizes.items():
        ctype = {'bool': '_Bool', 'pointer': 'void *'}.get(name, name.replace('-', ' '))
        assertions.append(f'_Static_assert(sizeof({ctype}) == {value}, "{name}");')
    assertions += [f'_Static_assert(CHAR_BIT == {char_bit}, "char-bit");',
                   f'_Static_assert(((char)-1 > 0) == {int(unsigned_char)}, "char-sign");']
    abi_check = output / 'gcc-abi.c'
    abi_check.write_text('\n'.join(assertions) + '\n')
    gcc(['-fsyntax-only', str(abi_check)])

    # GCC resolves real headers, builtins, include_next and conditional branches.
    # Do not rewrite declarations or substitute analyzer-only header stubs.
    preprocessed = output / 'decoder-functions.i'
    preprocessed.write_text(gcc(['-E', str(generated)]))
    search_command = [args.cc, *compile_flags, '-E', '-v', str(generated)]
    commands.append(search_command)
    search = subprocess.run(search_command, capture_output=True, text=True, check=True)
    (output / 'gcc-header-search.log').write_text(search.stderr)

    # std.cfg defines errno_t as a macro. Real headers declare it as a typedef.
    # The .i file is already preprocessed; keep its identifiers unchanged.
    command = [args.cppcheck, '--language=c', '--std=c11', '--enable=all',
               '--check-level=exhaustive', '--library=posix', '--error-exitcode=1',
               '--platform=' + str(platform_path), '-Uerrno_t', '--xml',
               '--xml-version=2', str(preprocessed)]
    commands.append(command)
    result = subprocess.run(command, capture_output=True, text=True)
    (output / 'cppcheck.stdout').write_text(result.stdout)
    (output / 'cppcheck.xml').write_text(result.stderr)
    findings = ET.fromstring(result.stderr).findall('errors/error')
    report = {'compiler': args.cc, 'triplet': gcc(['-dumpmachine']).strip(),
              'cppcheck': subprocess.check_output([args.cppcheck, '--version'], text=True).strip(),
              'commands': commands, 'returncode': result.returncode,
              'preprocessed_sha256': hashlib.sha256(preprocessed.read_bytes()).hexdigest(),
              'findings': [dict(item.attrib, locations=[dict(loc.attrib) for loc in item.findall('location')])
                           for item in findings]}
    (output / 'cppcheck-result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(result.stdout, end='')
    print(result.stderr, end='')
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--cc', required=True)
    parser.add_argument('--pkg-config', default='pkg-config')
    parser.add_argument('--cflags', default='')
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--analyze', action='store_true')
    parser.add_argument('--runner', default='', help='target execution command prefix')
    parser.add_argument('--compile-only', action='store_true', help='build without execution')
    parser.add_argument('--cppcheck', metavar='PROGRAM',
                        help='analyze with GCC preprocessing instead of building or running')
    args = parser.parse_args()
    version = subprocess.check_output([args.cc, '-dumpfullversion'], text=True).strip()
    if version.split('.')[0] != '16':
        parser.error('the test requires GCC 16')
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.source.resolve() / 'util/cairo-script'
    functions = [extract(source / 'cairo-script-file.c', 'csi_file_new_from_string')]
    functions += [extract(source / 'cairo-script-operators.c', name)
                  for name in ['inflate_string', '_image_read_raw']]
    fixture_path = pathlib.Path(__file__).with_suffix('.c').resolve()
    fixture = fixture_path.read_text()
    generated = args.output / 'decoder-functions.c'
    fixture_line = f'#line 1 "{fixture_path.as_posix()}"\n'
    generated.write_text(fixture_line + fixture + '\n' + '\n'.join(functions) +
                         '\n#define TEST_MAIN\n' + fixture_line + fixture)
    include_flags = shlex.split(subprocess.check_output(
        [args.pkg_config, '--cflags', 'cairo', 'lzo2'], text=True))
    library_flags = shlex.split(subprocess.check_output(
        [args.pkg_config, '--libs', 'cairo', 'lzo2'], text=True))
    executable = args.output / 'cairo-lzo-bounds'
    command = [args.cc, '-std=c11', '-g', '-O1', '-Wall', '-Wextra']
    if args.sanitize:
        command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if args.analyze:
        command += ['-fanalyzer']
    command += shlex.split(args.cflags)
    command += include_flags
    if args.cppcheck:
        return cppcheck(args, generated, command[1:])
    command += [str(generated), '-o', str(executable), *library_flags, '-lz']
    print(shlex.join(command), flush=True)
    subprocess.run(command, check=True)
    if args.compile_only:
        print('Compiled only; no runtime acceptance.')
        return 0
    runner = shlex.split(args.runner)
    failed = 0
    total = 0
    for entry in ['file', 'font', 'image']:
        cases = ['valid', 'overflow', 'short', 'truncated', 'trailing']
        if entry != 'image':
            cases += ['intmax', 'uintmax', 'negative']
        if entry == 'file':
            cases += ['string-oom']
        for case in cases:
            total += 1
            failed += subprocess.run([*runner, str(executable), entry, case]).returncode != 0
    print(f'{total - failed}/{total} cases passed')
    return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main())
