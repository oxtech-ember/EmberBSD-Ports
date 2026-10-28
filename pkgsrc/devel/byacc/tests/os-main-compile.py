#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Compile the prepared byacc main with both OS cleanup configurations."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
for option in ('source', 'config', 'clang', 'sysroot', 'work'):
    p.add_argument('--' + option, type=Path, required=True)
a = p.parse_args()
a.work.mkdir(parents=True, exist_ok=False)
for cleanup in (False, True):
    command = [str(a.clang), '--target=aarch64--netbsd', '--sysroot=' + str(a.sysroot),
               '-std=gnu11', '-Wall', '-Werror', '-DHAVE_CONFIG_H',
               '-DMAXTABLE=INT_MAX', '-DGCC_NORETURN=__dead',
               '-I' + str(a.config), '-I' + str(a.source)]
    if cleanup:
        command.append('-DNO_LEAKS')
    command += ['-c', str(a.source / 'main.c'), '-o', str(a.work / ('cleanup.o' if cleanup else 'normal.o'))]
    subprocess.run(command, check=True)
    print('PASS: NO_LEAKS=' + str(cleanup))
