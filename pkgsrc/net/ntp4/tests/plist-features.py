#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check package inventory against ordinary configured feature selections."""
from pathlib import Path
import subprocess
import sys
import tempfile

script = Path(__file__).resolve().parents[1] / 'files/plist-features.py'
with tempfile.TemporaryDirectory() as directory:
    status = Path(directory) / 'config.status'
    status.write_text('S["NTPTIME_DS"]="ntptime"\nS["TICKADJ_DS"]=""\n'
                      'S["CALC_TICKADJ_DS"]=""\nS["TIMETRIM_DS"]=""\n')
    run = lambda: subprocess.run([sys.executable, '-B', str(script), str(status)],
                                 text=True, capture_output=True)
    result = run()
    assert result.returncode == 0 and result.stdout.splitlines() == ['sbin/ntptime']
    status.write_text('S["NTPTIME_DS"]="ntptime"\nS["TICKADJ_DS"]="tickadj"\n'
                      'S["CALC_TICKADJ_DS"]="calc_tickadj"\nS["CALC_TICKADJ_MS"]="8"\n'
                      'S["TIMETRIM_DS"]=""\n')
    result = run()
    assert result.returncode == 0 and set(result.stdout.splitlines()) == {
        'sbin/ntptime', 'sbin/tickadj', 'sbin/calc_tickadj', 'man/man8/calc_tickadj.8'}
    status.write_text('S["NTPTIME_DS"]="unknown"\n')
    assert run().returncode != 0
print('NTP configured optional package inventory: PASS')
