#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Verify the producer uses the same SDK lock as target readers."""
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile

if len(sys.argv) != 4:
    raise SystemExit('usage: host-tools-lock.py SDK_SOURCE PYTHON SHELL')
sdk, python, shell = sys.argv[1:]
sys.path.insert(0, str(Path(sdk) / 'src'))
from emberbsd_sdk import process
runner = Path(__file__).resolve().parents[1] / 'cross/run-host-tools.py'
with tempfile.TemporaryDirectory(prefix='qt-host-lock-') as tmp:
    root = Path(tmp).resolve()
    work = str(root / 'work')
    env = os.environ.copy()
    env.update(HOST_SDK_SOURCE=sdk, QT_HOST_LOCK_ROOT=str(root), HOST_SH=shell)
    cmd = [python, '-I', '-S', str(runner), str(root), work]
    for resource in (work, str(Path(work) / 'qtbase')):
        with process.ContextLocks([resource], str(root), shared=True):
            blocked = subprocess.run(cmd, env=env, text=True, capture_output=True)
        if blocked.returncode == 0 or 'object context is busy' not in blocked.stderr:
            raise SystemExit('producer did not respect target reader lock: ' + resource)
    Path(work).mkdir()
    (Path(work) / 'qtbase').symlink_to(root)
    noncanonical = subprocess.run(cmd, env=env, text=True, capture_output=True)
    if noncanonical.returncode == 0 or 'Qt host prefix must use its canonical' not in noncanonical.stderr:
        raise SystemExit('symlinked Qt host prefix accepted')
    (Path(work) / 'qtbase').unlink()
    direct = subprocess.run([shell, str(runner.with_name('build-host-tools.sh')), str(root), work], env=env, text=True, capture_output=True)
    if direct.returncode == 0 or 'Use run-host-tools.py' not in direct.stderr:
        raise SystemExit('direct shell producer did not require lock entrypoint')
    unblocked = subprocess.run(cmd, env=env, text=True, capture_output=True)
    if 'object context is busy' in unblocked.stderr:
        raise SystemExit('producer lock remained busy after reader exit')
    if unblocked.returncode == 0:
        raise SystemExit('fixture unexpectedly built without required tools')
    # Exercise the real entrypoint with an isolated producer that leaves a
    # background child; the SDK supervisor must drain it before unlocking.
    isolated = root / 'isolated'
    isolated.mkdir()
    shutil.copyfile(runner, isolated / 'run-host-tools.py')
    producer = isolated / 'build-host-tools.sh'
    producer.write_text("\"$HOST_SH\" -c 'trap \"\" HUP; /bin/sleep 20' &\n" +
                        'echo $! > "' + str(root / 'child.pid') + '"\n/bin/sleep 1\n')
    result = subprocess.run([python, '-I', '-S', str(isolated / 'run-host-tools.py'),
                             str(root), work], env=env, text=True, capture_output=True)
    if result.returncode == 0 or 'left live descendants' not in result.stderr:
        raise SystemExit('producer descendant test failed: ' + result.stderr)
    child = int((root / 'child.pid').read_text())
    try:
        os.kill(child, 0)
    except ProcessLookupError:
        pass
    else:
        raise SystemExit('producer child survived lock release')
    with process.ContextLocks([work], str(root), shared=True):
        pass
print('PASS: target reader blocks host writer and release permits entry')
