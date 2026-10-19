#!/usr/bin/env python3
"""Compare the actual Sway seat destroy handler with ASan/UBSan."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('baseline', 'patched', 'wayland', 'wayland-include', 'work'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
assert all(x.is_absolute() for x in vars(a).values()) and not a.work.exists()
a.work.mkdir(parents=True)
prefix, main = Path(__file__).with_suffix('.c').read_text().split('/* ACTUAL HANDLER */')
records = []
for label, source in (('baseline', a.baseline), ('patched', a.patched)):
    text = (source / 'sway/input/seat.c').read_text()
    start = text.index('static void handle_seat_destroy(')
    brace = text.index('{', start)
    end, depth = brace + 1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    generated = a.work / (label + '.c')
    generated.write_text(prefix + (source / 'common/list.c').read_text() +
                         text[start:end] + main)
    binary = a.work / label
    command = ['/usr/bin/cc', '-std=c11', '-O1', '-g', '-D_DARWIN_C_SOURCE',
        '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra',
        '-Werror', '-Wno-unused-parameter', '-fsanitize=address,undefined',
        '-fno-omit-frame-pointer', '-I' + str(source / 'include'),
        '-I' + str(a.wayland_include), '-I' + str(a.wayland / 'src'),
        str(generated), str(source / 'common/log.c'),
        str(a.wayland / 'src/wayland-util.c'), '-o', str(binary)]
    built = subprocess.run(command, text=True, capture_output=True, timeout=60)
    (a.work / (label + '-build.log')).write_text(built.stdout + built.stderr)
    assert built.returncode == 0, built.stderr
    for case in ('absent', 'current', 'other'):
        result = subprocess.run([str(binary), case], text=True, capture_output=True,
            env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:abort_on_error=1',
                 'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}, timeout=10)
        record = dict(source=label, case=case, status=result.returncode,
                      stdout=result.stdout, stderr=result.stderr)
        records.append(record)
        (a.work / 'receipt.json').write_text(json.dumps(records, indent=2) + '\n')
        if label == 'baseline' and case == 'absent':
            assert result.returncode != 0 and 'runtime error:' in result.stderr
            assert 'null pointer' in result.stderr
        else:
            assert result.returncode == 0, record
            assert 'AddressSanitizer' not in result.stderr and 'runtime error:' not in result.stderr
print('PASS: original NULL-config failure; absent/current/other cleanup ownership under ASan/UBSan')
