#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Inspect RV32 builtins and link fixed/PIE consumers without libc or OS headers."""
import argparse
import json
from pathlib import Path
import re
import shlex
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files'))
import source as owner
arguments = owner.load_sdk(sys.argv[1:])
cli = argparse.ArgumentParser(description=__doc__)
for name in ('host-prefix', 'archive', 'work'):
    cli.add_argument('--' + name, type=Path, required=True)
cli.add_argument('--build-dir', type=Path, help='inspect the actual producer CMake/Ninja commands')
cli.add_argument('--nonpic-archive', type=Path, help='require rejection of a previous non-PIC archive')
args = cli.parse_args(arguments)
from emberbsd_sdk import host_prefix, process
from emberbsd_sdk.errors import CommandError

native = host_prefix.load_host_prefix(args.host_prefix, compiler_family='clang',
    required_roles=('cc', 'nm', 'llvm-readobj', 'python', 'ninja', 'elf-ld'))
assert Path(sys.executable).resolve() == Path(native.tool('python')).resolve()
archive = args.archive.resolve(strict=True)
work = Path(args.work)
assert work.is_absolute() and not work.exists()
work.mkdir()
work = work.resolve()
sysroot = work / 'sysroot'
sysroot.mkdir()
environment = process.sanitized_environment()
environment['PATH'] = native.path


def run(command):
    return process.capture(command, cwd=str(work), env=environment).stdout.decode()


compile_count = None
if args.build_dir:
    cache = (args.build_dir / 'CMakeCache.txt').read_text()
    assert re.search(r'^CMAKE_LINKER:[^=]+=' + re.escape(native.tool('elf-ld')) + r'$', cache, re.M)
    assert re.search(r'^COMPILER_RT_BUILTINS_ENABLE_PIC:BOOL=ON$', cache, re.M)
    assert re.search(r'^COMPILER_RT_HAS_FPIC_FLAG:INTERNAL=1$', cache, re.M)
    commands = run([native.tool('ninja'), '-C', str(args.build_dir), '-t', 'commands', 'builtins'])
    compilations = [words for line in commands.splitlines()
                    if '-c' in (words := shlex.split(line))]
    assert compilations
    assert all('-fPIC' in words for words in compilations)
    compile_count = len(compilations)

headers = json.loads(run([native.tool('llvm-readobj'), '--elf-output-style=JSON', '--file-headers', str(archive)]))
assert headers
for member in headers:
    header = member['ElfHeader']
    assert member['FileSummary']['Format'] == 'elf32-littleriscv'
    assert header['Ident']['Class']['Value'] == 1
    assert header['Ident']['DataEncoding']['Value'] == 1
    assert header['Machine']['Value'] == 243
    assert header['Type'] == 'Relocatable (0x1)'
    # RVC is permitted; the float-ABI and RVE bits must all be clear.
    assert header['Flags']['Value'] in (0, 1), member
attributes = run([native.tool('llvm-readobj'), '--arch-specific', str(archive)])
arches = re.findall(r'^\s*Value: (rv32\S+)$', attributes, re.M)
assert len(arches) == len(headers), (len(arches), len(headers))
for arch in arches:
    extensions = {re.match(r'[a-z]+', word)[0] for word in arch.split('_')[1:]}
    assert arch.startswith('rv32i')
    assert {'m', 'a', 'c', 'zicsr', 'zifencei'} <= extensions
    assert extensions <= {'m', 'a', 'c', 'zicsr', 'zifencei', 'zmmul', 'zaamo', 'zalrsc', 'zca'}
symbols = run([native.tool('nm'), '--defined-only', '--extern-only', '--just-symbol-name', str(archive)])
assert '__ashldi3' in symbols.splitlines()
fixture = work / 'shift.c'
fixture.write_text('unsigned long long shift(unsigned long long x, unsigned n) { return x << n; }\n')
flags = ['--no-default-config', '--target=riscv32-unknown-elf', '-march=rv32imac_zicsr_zifencei',
         '-mabi=ilp32', '-ffreestanding', '--sysroot=' + str(sysroot), '-Oz']
obj = work / 'shift.o'
run([native.tool('cc'), *flags, '-c', str(fixture), '-o', str(obj)])
undefined = run([native.tool('nm'), '--undefined-only', '--just-symbol-name', str(obj)])
assert '__ashldi3' in undefined.splitlines(), undefined
linked = work / 'shift.elf'
run([native.tool('cc'), *flags, '-fuse-ld=lld', '-nostdlib', '-Wl,--no-undefined', '-Wl,-e,shift',
     str(obj), str(archive), '-o', str(linked)])
assert not run([native.tool('nm'), '--undefined-only', '--just-symbol-name', str(linked)]).strip()
linked_header = json.loads(run([native.tool('llvm-readobj'), '--elf-output-style=JSON', '--file-headers', str(linked)]))[0]
assert linked_header['FileSummary']['Format'] == 'elf32-littleriscv'
assert linked_header['ElfHeader']['Flags']['Value'] in (0, 1)

# __absvsi2 passes __FILE__/__func__ strings to its abort helper. This pulls
# real data-address relocations into the PIE, which __ashldi3 alone cannot test.
pic_source = work / 'pie.c'
pic_source.write_text('extern int __absvsi2(int);\n'
    'unsigned long long consumer(unsigned long long x, unsigned n, int y) {\n'
    '    return (x << n) + __absvsi2(y);\n}\n')
pic_object = work / 'pie.o'
run([native.tool('cc'), *flags, '-fPIE', '-c', str(pic_source), '-o', str(pic_object)])
undefined = run([native.tool('nm'), '--undefined-only', '--just-symbol-name', str(pic_object)])
assert {'__ashldi3', '__absvsi2'} <= set(undefined.splitlines())
pie = work / 'consumer.elf'
link = [native.tool('elf-ld'), '-pie', '--no-dynamic-linker', '-z', 'text', '--no-undefined',
        '-e', 'consumer', str(pic_object)]
run([*link, str(archive), '-o', str(pie)])
assert not run([native.tool('nm'), '--undefined-only', '--just-symbol-name', str(pie)]).strip()
pie_header = json.loads(run([native.tool('llvm-readobj'), '--elf-output-style=JSON', '--file-headers', str(pie)]))[0]
assert pie_header['FileSummary']['Format'] == 'elf32-littleriscv'
assert pie_header['ElfHeader']['Type'] == 'SharedObject (0x3)'
assert pie_header['ElfHeader']['Flags']['Value'] in (0, 1)
assert 'TEXTREL' not in run([native.tool('llvm-readobj'), '--dynamic-table', str(pie)])
if args.nonpic_archive:
    try:
        run([*link, str(args.nonpic_archive.resolve(strict=True)), '-o', str(work / 'nonpic.elf')])
    except CommandError as error:
        diagnostic = error.stderr.decode()
        assert 'recompile with -fPIC' in diagnostic and 'absvsi2.c.obj' in diagnostic, diagnostic
        (work / 'nonpic-rejected.log').write_text(diagnostic)
    else:
        raise AssertionError('non-PIC data references unexpectedly linked as a PIE')
assert list(sysroot.iterdir()) == []
result = dict(status='PASS', archive=str(archive), members=len(headers),
              abi='RV32IMAC_Zicsr_Zifencei ILP32 soft-float', ashldi3=True, oz_link=True,
              pie_link=True, pic_compile_commands=compile_count,
              nonpic_rejected=bool(args.nonpic_archive), execution=False)
(work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
