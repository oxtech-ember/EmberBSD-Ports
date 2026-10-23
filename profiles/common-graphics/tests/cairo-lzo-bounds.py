#!/usr/bin/env python3
"""Compile exact Cairo decoder functions with guarded allocation fixtures.

Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: MIT
The supplied source must be a verified Cairo release or its patched copy.
This focused host check is not a complete Cairo package or target runtime test.
"""
import argparse
import pathlib
import re
import shlex
import subprocess


def extract(path, name):
    text = path.read_text()
    match = re.search(r'^' + re.escape(name) + r' \(', text, re.M)
    if match is None:
        raise ValueError(f'missing production function {name}: {path}')
    start = text.rfind('\n', 0, match.start() - 1) + 1
    end = text.index('\n}', match.end()) + 2
    line = text.count('\n', 0, start) + 1
    return f'#line {line} "{path.as_posix()}"\n' + text[start:end] + '\n'


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
    args = parser.parse_args()
    version = subprocess.check_output([args.cc, '-dumpfullversion'], text=True).strip()
    if version.split('.')[0] != '16':
        parser.error('the test requires GCC 16')
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.source.resolve() / 'util/cairo-script'
    functions = [extract(source / 'cairo-script-file.c', 'csi_file_new_from_string')]
    functions += [extract(source / 'cairo-script-operators.c', name)
                  for name in ['inflate_string', '_image_read_raw']]
    fixture = pathlib.Path(__file__).with_suffix('.c').read_text()
    generated = args.output / 'decoder-functions.c'
    generated.write_text(fixture + '\n' + '\n'.join(functions) +
                         '\n#define TEST_MAIN\n' + fixture)
    flags = shlex.split(subprocess.check_output(
        [args.pkg_config, '--cflags', '--libs', 'cairo', 'lzo2'], text=True))
    executable = args.output / 'cairo-lzo-bounds'
    command = [args.cc, '-std=c11', '-g', '-O1', '-Wall', '-Wextra']
    if args.sanitize:
        command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if args.analyze:
        command += ['-fanalyzer']
    command += shlex.split(args.cflags)
    command += [str(generated), '-o', str(executable), *flags, '-lz']
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
