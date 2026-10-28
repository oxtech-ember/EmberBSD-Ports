#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check V8 host PaX wrapper qualification and argument preservation."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
a = parser.parse_args()
wrapper = a.source / 'tools/run-paxctl.py'
with tempfile.TemporaryDirectory(prefix='v8 paxctl test ') as d:
    d = Path(d)
    target = d / 'qualified paxctl'
    output = d / 'arguments.json'
    target.write_text('#!' + sys.executable + '\nimport json,sys\nwith open(sys.argv[1], "w") as f: json.dump(sys.argv[2:], f)\n')
    target.chmod(0o755)
    stamp = d / 'stamp'
    r = subprocess.run([sys.executable, str(wrapper), str(stamp), str(target), str(output), '+m', 'mksnapshot with spaces'], capture_output=True, text=True)
    assert r.returncode == 0 and stamp.exists(), r.stderr
    assert json.loads(output.read_text()) == ['+m', 'mksnapshot with spaces']
    target.write_text('#!' + sys.executable + '\nimport sys\nsys.exit(7)\n')
    r = subprocess.run([sys.executable, str(wrapper), str(stamp), str(target)], capture_output=True, text=True)
    assert r.returncode == 7 and not stamp.exists(), 'failed action left a stale stamp'
    target.write_text('#!' + sys.executable + '\nimport sys\nsys.exit(0)\n')
    r = subprocess.run([sys.executable, str(wrapper), str(stamp), str(target)], capture_output=True, text=True)
    assert r.returncode == 0 and stamp.exists(), 'successful retry failed'
    target.write_text('#!' + sys.executable + '\nimport time\ntime.sleep(0.5)\n')
    try:
        subprocess.run([sys.executable, str(wrapper), str(stamp), str(target)], timeout=0.2, capture_output=True)
        raise AssertionError('expected wrapper timeout')
    except subprocess.TimeoutExpired:
        assert not stamp.exists(), 'timed out action left a stale stamp'
    r = subprocess.run([sys.executable, str(wrapper), str(stamp), 'paxctl', '+m', 'mksnapshot'], capture_output=True, text=True)
    assert r.returncode != 0 and not stamp.exists()
print('V8 PaX wrapper: selected absolute tool and argv; relative tool rejected')
