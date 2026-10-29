#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Upstream status: not submitted.
"""Compare the common standalone keyword generator with upstream host builds."""
import argparse
import subprocess
import tempfile
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'clang', 'linker', 'host-sdk', 'byacc', 'bison',
             'original-byacc', 'original-bison', 'work-dir'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
assert all(getattr(a, name).is_absolute() for name in vars(a))
with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    root = Path(tmp)
    for mode in ('byacc', 'bison'):
        work = root / mode
        work.mkdir()
        if mode == 'byacc':
            subprocess.run([str(a.byacc), '-d', '-b', 'ntp_parser',
                            str(a.source / 'ntpd/ntp_parser.y')], cwd=work, check=True)
            (work / 'ntp_parser.tab.h').rename(work / 'ntp_parser.h')
        else:
            subprocess.run([str(a.bison), '-d', '-o', str(work / 'ntp_parser.c'),
                            str(a.source / 'ntpd/ntp_parser.y')], cwd=work, check=True)
        subprocess.run([str(a.clang), '--ld-path=' + str(a.linker),
                        '--sysroot=' + str(a.host_sdk), '-std=c11', '-Wall', '-Wextra',
                        '-Werror', '-I' + str(work), '-I' + str(a.source / 'ntpd'),
                        str(a.source / 'ntpd/keyword-gen.c'), '-o', str(work / 'gen')], check=True)
        header = str(work / 'ntp_parser.h')
        # Original is compiled for the corresponding generated token header.
        results = [subprocess.run([str(gen), header], capture_output=True, check=True)
                   for gen in (getattr(a, 'original_' + mode), work / 'gen')]
        def normal(data):
            return b''.join(line for line in data.splitlines(keepends=True)
                            if b'diff_ignore_line' not in line)
        assert normal(results[0].stdout) == normal(results[1].stdout)
        assert results[0].stderr == results[1].stderr
        print(mode + ': original/standalone output PASS (generated timestamp excluded)')
