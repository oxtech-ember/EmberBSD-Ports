#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Run the native Qt producer while holding its shared SDK work lock."""
import os
from pathlib import Path
import signal
import sys
import time

if len(sys.argv) != 3:
    raise SystemExit('usage: run-host-tools.py DISTFILES ABSOLUTE_WORK')
paths = [sys.argv[1], sys.argv[2], os.environ.get('HOST_SDK_SOURCE', ''),
         os.environ.get('QT_HOST_LOCK_ROOT', ''), os.environ.get('HOST_SH', '')]
if any(not os.path.isabs(value) for value in paths):
    raise SystemExit('absolute DISTFILES, WORK, HOST_SDK_SOURCE, QT_HOST_LOCK_ROOT and HOST_SH required')
distfiles, work, sdk, lock_root, shell = paths
if os.path.realpath(work) != work:
    raise SystemExit('WORK must use its canonical absolute path')
qtbase = os.path.join(work, 'qtbase')
if os.path.realpath(qtbase) != qtbase:
    raise SystemExit('Qt host prefix must use its canonical absolute path')
sys.path.insert(0, str(Path(sdk) / 'src'))
from emberbsd_sdk import process

producer = Path(__file__).resolve().with_name('build-host-tools.sh')
argv = [shell, str(producer), distfiles, work]

def interrupt(_number, _frame):
    raise KeyboardInterrupt

for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(signum, interrupt)
with process.ContextLocks([work, qtbase], lock_root):
    env = os.environ.copy()
    env["QT_HOST_LOCKED"] = "1"
    group = process.OwnedProcessGroup(argv, cwd=None, env=env, stdout=None, stderr=None)
    try:
        group.start()
        while (code := group.poll()) is None:
            time.sleep(0.05)
        if group.alive():
            raise process.SDKError('Qt host producer left live descendants')
    finally:
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(signum, signal.SIG_IGN)
        group.stop()
sys.exit(code)
