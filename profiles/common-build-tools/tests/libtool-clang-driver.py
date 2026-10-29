#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Verify C and C++ libtool links retain selected Clang driver flags."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('libtool', 'host-prefix', 'target-tools', 'sysroot', 'runtime', 'work-dir'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
host, sysroot, runtime = a.host_prefix, a.sysroot, a.runtime
env = dict(os.environ, PATH=':'.join(map(str, (a.target_tools / 'bin', host / 'bin', host / 'gnu/bin'))),
           TMPDIR=str(a.work_dir))
with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    work = Path(tmp)
    resource_path = work / 'resource directory'
    resource_path.symlink_to(runtime / 'lib/clang/23', target_is_directory=True)
    for lang in ('c', 'cxx'):
        compiler = host / 'bin' / ('clang' if lang == 'c' else 'clang++')
        tag = 'CC' if lang == 'c' else 'CXX'
        source = work / ('sample.c' if lang == 'c' else 'sample.cc')
        source.write_text('int example(void) { return 1; }\n')
        base = [str(compiler), '--target=aarch64--netbsd', '--sysroot=' + str(sysroot)]
        if lang == 'cxx':
            base += ['-nostdinc++', '-isystem', str(runtime / 'include/c++/v1')]
        command = [str(host / 'bin/mksh'), str(a.libtool), '--tag=' + tag,
                   '--mode=compile', *base, '-fPIC', '-c', str(source), '-o', 'sample.lo']
        subprocess.run(command, env=env, cwd=work, check=True, capture_output=True, text=True)
        for form in ('attached', 'separate', 'single-attached'):
            resource = str(resource_path)
            rtlib = '-rtlib' if form.startswith('single-') else '--rtlib'
            attached = form.endswith('attached')
            flags = (['-resource-dir=' + resource, rtlib + '=compiler-rt'] if attached
                     else ['-resource-dir', resource, rtlib, 'compiler-rt'])
            flags += ['--unwindlib=libunwind', '--ld-path=' + str(host / 'bin/ld.lld'),
                      '-L' + str(runtime / 'lib'), '-Wl,-rpath-link,' + str(runtime / 'lib')]
            if lang == 'cxx':
                flags += ['-stdlib=libc++']
            name = f'libsample-{lang}-{form}'
            command = [str(host / 'bin/mksh'), str(a.libtool), '--tag=' + tag, '--mode=link',
                       *base, *flags, '-o', name + '.la', 'sample.lo', '-rpath', '/usr/lib']
            result = subprocess.run(command, env=env, cwd=work, capture_output=True, text=True)
            if result.returncode:
                raise SystemExit(result.stdout + result.stderr)
            line = next((line for line in result.stdout.splitlines()
                         if ': link:' in line and ' -shared ' in line), '')
            words = shlex.split(line.partition(': link:')[2])
            required = (['-resource-dir=' + resource, rtlib + '=compiler-rt'] if attached
                        else ['-resource-dir', resource, rtlib, 'compiler-rt'])
            required += ['--ld-path=' + str(host / 'bin/ld.lld')]
            if not all(flag in words for flag in required):
                raise SystemExit('selected driver flag lost: ' + line)
            elf = work / '.libs' / (name + '.so')
            check = subprocess.check_output([str(host / 'bin/llvm-readelf'), '-h', str(elf)], env=env, text=True)
            if 'AArch64' not in check:
                raise SystemExit('link output is not AArch64 ELF')
    for flag in ('-resource-dir', '--rtlib'):
        result = subprocess.run([str(host / 'bin/mksh'), str(a.libtool), '--tag=CC',
                                 '--mode=link', str(host / 'bin/clang'), flag],
                                env=env, cwd=work, capture_output=True, text=True)
        if result.returncode == 0 or 'requires an argument' not in result.stderr:
            raise SystemExit('missing-argument diagnostic failed: ' + flag)
print('libtool Clang C/C++ driver flags: PASS (6 links, 2 missing arguments)')
