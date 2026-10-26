#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the actual AArch64 linker MRI TRUNCATE and MAP option paths."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--prefix', required=True, type=Path)
parser.add_argument('--work', required=True, type=Path)
args = parser.parse_args()
work = args.work.resolve()
work.mkdir(exist_ok=False)
tools = {name: str(args.prefix.resolve() / 'bin' / ('aarch64--netbsd-' + name))
         for name in ('as', 'ld', 'readelf')}


def run(name, *arguments):
    result = subprocess.run([tools[name], *map(str, arguments)], cwd=work,
                            text=True, capture_output=True)
    with (work / 'commands.log').open('a') as stream:
        stream.write(repr(result.args) + '\n' + result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit('linker option regression failed; inspect ' + str(work / 'commands.log'))
    return result.stdout


(work / 'input.s').write_text('.text\n.globl _start\n_start:\n nop\n'
    '.globl deliberately_long_symbol_name\ndeliberately_long_symbol_name:\n nop\n')
run('as', '-o', 'input.o', 'input.s')
for option in ('', 'MAP(F)\n'):
    (work / 'link.ld').write_text(option + 'SECTIONS { . = 0x10000; .text : { *(.text) } }\n')
    output = 'map.elf' if option else 'plain.elf'
    run('ld', '-T', 'link.ld', '-o', output, 'input.o')
if (work / 'map.elf').read_bytes() != (work / 'plain.elf').read_bytes():
    raise SystemExit('MAP(F) changed linked output')
for option in ('', 'TRUNCATE 3\n'):
    (work / 'link.mri').write_text(option + 'BASE 0x10000\nLOAD input.o\nEND\n')
    output = 'truncate.elf' if option else 'mri.elf'
    run('ld', '-c', 'link.mri', '-o', output)
if (work / 'truncate.elf').read_bytes() != (work / 'mri.elf').read_bytes():
    raise SystemExit('MRI TRUNCATE changed linked output')
for output in ('map.elf', 'truncate.elf'):
    header = run('readelf', '-h', output)
    symbols = run('readelf', '-sW', output)
    if 'AArch64' not in header or 'deliberately_long_symbol_name' not in symbols:
        raise SystemExit('linker lost the target or full symbol name')
print('real AArch64 MAP(F) and MRI TRUNCATE preserve linked bytes and full symbols')
