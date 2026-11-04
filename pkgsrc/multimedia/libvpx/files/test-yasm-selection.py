#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run upstream configure without which and verify the selected assembler."""
import argparse
import os
import shlex
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--prefix', type=Path, required=True)
parser.add_argument('--cc', type=Path, required=True)
parser.add_argument('--sysroot', type=Path, required=True)
parser.add_argument('--pkgsrc', type=Path, required=True)
parser.add_argument('--makeconf', type=Path, required=True)
parser.add_argument('--bmake', type=Path, required=True)
args = parser.parse_args()
prefix = args.prefix.resolve()
query = subprocess.run([str(args.bmake), '-C', str(args.pkgsrc / 'multimedia/libvpx'),
                        'MAKECONF=' + str(args.makeconf), '-V', '${CONFIGURE_ENV:MAS=*}'],
                       check=True, capture_output=True, text=True, timeout=45)
assignments = shlex.split(query.stdout)
assert assignments == ['AS=' + str(prefix / 'bin/yasm')], assignments
with tempfile.TemporaryDirectory(prefix='libvpx-yasm-') as temporary:
    root = Path(temporary)
    tools = root / 'tools'
    tools.mkdir()
    (tools / 'awk').symlink_to(prefix / 'bin/nawk')
    path = ':'.join(map(str, (tools, prefix / 'bin', prefix / 'gnu/bin')))
    assert all(not (Path(directory) / 'which').exists() for directory in path.split(':'))
    for name, selected in [('old', False), ('new', True)]:
        work = root / name
        work.mkdir()
        env = dict(os.environ, PATH=path)
        env.pop('AS', None)
        env['CC'] = str(args.cc.absolute())
        env['CFLAGS'] = '--target=x86_64--netbsd --sysroot=' + str(args.sysroot.resolve())
        env['LD'] = env['CC']
        env['LDFLAGS'] = env['CFLAGS']
        if selected:
            env['AS'] = assignments[0][3:]
        result = subprocess.run([str(prefix / 'bin/bash'), str(args.source / 'configure'),
                                 '--target=x86_64-linux-gcc', '--disable-unit-tests'],
                                cwd=work, env=env, capture_output=True, text=True)
        if not selected:
            assert result.returncode != 0 and 'Neither yasm nor nasm have been found' in result.stdout + result.stderr
        else:
            assert result.returncode == 0, result.stdout + result.stderr
            assert 'AS=' + str(prefix / 'bin/yasm') in (work / 'libs-x86_64-linux-gcc.mk').read_text()
            assert '-f elf64' in (work / 'libs-x86_64-linux-gcc.mk').read_text()
    assembly = root / 'probe.asm'
    assembly.write_text('section .text\nglobal ember_probe\nember_probe:\n ret\n')
    obj = root / 'probe.o'
    subprocess.run([str(prefix / 'bin/yasm'), '-f', 'elf64', '-o', str(obj), str(assembly)], check=True)
    info = subprocess.run([str(prefix / 'bin/llvm-readobj'), '--file-headers', str(obj)],
                          check=True, capture_output=True, text=True).stdout
    assert 'Format: elf64-x86-64' in info
    print('PASS: old configure fails; selected yasm configures and emits amd64 ELF')
