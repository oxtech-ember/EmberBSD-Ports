#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted).
"""Run the actual queue dependency functions with an asynchronous sync backend."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('--cc', required=True)
parser.add_argument('--work', required=True, type=Path)
a = parser.parse_args()
s = a.source.read_text()
functions = []
for name in ('pvr_update_job_syncs', 'pvr_process_queue_signals', 'pvr_process_queue_waits'):
    pos = s.index(name + '(')
    start = s.rfind('static ', 0, pos)
    body = s.index('{', pos)
    depth = 1
    end = body + 1
    while depth:
        depth += (s[end] == '{') - (s[end] == '}')
        end += 1
    functions.append(s[start:end])
a.work.mkdir(parents=True, exist_ok=True)
fixture = Path(__file__).with_suffix('.c').read_text()
output = a.work / 'queue-syncs.c'
output.write_text(fixture.replace('/* ACTUAL_FUNCTIONS */', '\n\n'.join(functions)))
exe = a.work / 'queue-syncs'
subprocess.run([a.cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
                '-Wno-unused-parameter', str(output), '-o', str(exe)], check=True)
subprocess.run([str(exe)], check=True)
