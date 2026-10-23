#!/usr/bin/env python3
"""Check Sway's actual IPC header before and after the unsigned-shift patch."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True, help='Original Sway source')
p.add_argument('--cc', type=Path, required=True, help='Common GCC16 target compiler')
p.add_argument('--sysroot', type=Path, required=True)
p.add_argument('--native-cc', type=Path, default=Path('/usr/bin/cc'))
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
assert all(x.is_absolute() for x in [a.source, a.cc, a.sysroot, a.native_cc, a.work])
assert not a.work.exists()
a.work.mkdir(parents=True)
tests = Path(__file__).resolve().parent
patch = tests.parents[2] / 'pkgsrc/wayland/sway/patches/patch-include_ipc.h'
records = []

def run(label, command, env=None):
    r = subprocess.run([str(x) for x in command], text=True, capture_output=True,
                       env=env, timeout=120)
    records.append(dict(label=label, command=[str(x) for x in command],
                        status=r.returncode, stdout=r.stdout, stderr=r.stderr))
    (a.work / 'receipt.json').write_text(json.dumps(records, indent=2) + '\n')
    return r

for label in ['baseline', 'patched']:
    source = a.work / label
    (source / 'include').mkdir(parents=True)
    shutil.copy2(a.source / 'include/ipc.h', source / 'include/ipc.h')
    if label == 'patched':
        r = subprocess.run(['patch', '-f', '-F', '0', '-p0', '-i', str(patch)],
                           cwd=source, text=True, capture_output=True)
        assert r.returncode == 0, r.stderr + r.stdout
    flags = ['-std=c11', '-Wall', '-Wextra', '-I' + str(source / 'include')]
    strict = run(label + '-gcc-strict', [a.cc, '--sysroot=' + str(a.sysroot),
        *flags, '-Wshift-overflow=2', '-Werror', '-fanalyzer', '-c',
        tests / 'ipc-values.c', '-o', source / 'target.o'])
    assert (strict.returncode == 0) == (label == 'patched'), records[-1]
    if label == 'baseline':
        assert 'shift' in strict.stderr and '31' in strict.stderr
    binary = source / 'native'
    native = run(label + '-native-build', [a.native_cc, *flags, '-O1', '-g',
        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
        tests / 'ipc-values.c', '-o', binary])
    assert native.returncode == 0, records[-1]
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    checked = run(label + '-native-runtime', [binary], env)
    assert (checked.returncode == 0) == (label == 'patched'), records[-1]
    if label == 'baseline':
        assert 'left shift of 1 by 31' in checked.stderr
    else:
        assert checked.stdout.startswith('PASS: 10 event wire values')
print('PASS: original GCC shift rejection and UBSan failure; patched wire and mask contracts')
