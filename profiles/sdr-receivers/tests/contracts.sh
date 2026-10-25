#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; synthetic decoder contracts, no hardware or network.
set -eu
[ "$#" -eq 2 ] || { echo 'Usage: contracts.sh AIS_CATCHER NEW_WORK' >&2; exit 2; }
: "${PY:?Select an absolute Python interpreter}"
exec "$PY" - "$1" "$2" "$(dirname "$0")" <<'PY'
import json
from pathlib import Path
import subprocess
import sys
binary, work, tests = map(Path, sys.argv[1:])
if not binary.is_absolute() or not binary.is_file():
    raise SystemExit('An absolute decoder executable is required')
work.mkdir()
subprocess.run([sys.executable, str(tests / 'synthetic.py'), str(work / 'iq')], check=True)
help_result = subprocess.run([str(binary), '-h'], capture_output=True, timeout=30)
(work / 'help.txt').write_bytes(help_result.stdout + help_result.stderr)
if help_result.returncode or b'RTLSDR' not in help_result.stdout + help_result.stderr:
    raise SystemExit('Missing RTL backend or help failure')
for name, expected in [('valid', 8), ('bad-fcs', 0)]:
    result = subprocess.run([str(binary), '-X', 'off', '-r', 'CF32',
                             str(work / 'iq' / (name + '.cf32')), '-s', '96000', '-o', '5'],
                            capture_output=True, timeout=30)
    (work / (name + '.jsonl')).write_bytes(result.stdout)
    (work / (name + '.log')).write_bytes(result.stderr)
    if result.returncode:
        raise SystemExit(f'{name}: decoder exit {result.returncode}')
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    if len(rows) != expected:
        raise SystemExit(f'{name}: expected {expected} messages, got {len(rows)}')
    if expected:
        a = [r for r in rows if r['mmsi'] == 123456789 and r['channel'] == 'A']
        b = [r for r in rows if r['mmsi'] == 987654321 and r['channel'] == 'B']
        if len(a) != 4 or len(b) != 4 or any(r.get('lat') != 0 or r.get('lon') != 0 for r in a):
            raise SystemExit('Channel, identity or valid zero position mismatch')
        if any(r.get('lat') != 91 or r.get('lon') != 181 for r in b):
            raise SystemExit('Unavailable-position protocol sentinel mismatch')
    print(f'PASS synthetic {name}: {len(rows)} messages')
print('PASS help, RTL backend, valid A/B and damaged RF-FCS rejection; no physical RF acceptance')
PY
