#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real CLI interruption with private descendants.
import ast
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
sys.dont_write_bytecode = True
from llvm_fixture import FILES, fixture, load_sdk, write_json
sdk, args = load_sdk()
if len(args) != 2:
    sys.exit('Use CMAKE NEW_WORK')
cmake, work = args[0], Path(args[1]).absolute()
work.mkdir()
cross = FILES.parents[3] / 'cross'


def present(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def sleeper(path, pids):
    path.write_text(f'''#!{sys.executable}
import os,pathlib,signal,time
child=os.fork()
if child == 0:
    while True: time.sleep(0.05)
def stopped(sig, frame):
    os.kill(child, signal.SIGTERM)
    os.waitpid(child, 0)
    raise SystemExit(128+sig)
for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT): signal.signal(sig, stopped)
pathlib.Path({str(pids)!r}).write_text(str(os.getpid())+' '+str(child))
while True: time.sleep(0.05)
''')
    path.chmod(0o755)


for kind in ('fetch', 'reuse'):
    for number in (signal.SIGTERM, signal.SIGHUP):
        case = work / (kind + '-' + signal.Signals(number).name)
        case.mkdir()
        pids = case / 'pids'
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        if kind == 'fetch':
            commands = case / 'bin'; commands.mkdir()
            sleeper(commands / 'curl', pids)
            env['PATH'] = str(commands) + ':' + os.environ['PATH']
            command = [sys.executable, '-B', str(cross / 'fetch-sysroot.py'), '--sdk-source', sdk, 'a' * 40, 'b' * 64, str(case / 'output')]
            accepted = case / 'output/receipt.json'
        else:
            value = fixture(case / 'fixture', sdk, cmake)
            sleeper(Path(value['cmake']), pids)
            write_json(case / 'input.json', value)
            (case / 'stage').mkdir()
            accepted = case / 'receipt.json'
            command = [sys.executable, '-B', str(FILES / 'reuse-package-stage.py'), '--sdk-source', sdk, 'record', str(case / 'input.json'), str(case / 'stage'), str(accepted)]
        process = None
        owned = []
        try:
            with (case / 'cli.log').open('wb') as log:
                process = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
                deadline = time.monotonic() + 15
                while not pids.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                assert pids.exists(), (case / 'cli.log').read_text()
                owned = list(map(int, pids.read_text().split()))
                os.kill(process.pid, number)
                status = process.wait(timeout=15)
                assert status == 128 + number, f'{kind}: expected {128 + number}, got {status}'
                deadline = time.monotonic() + 3
                while any(present(pid) for pid in owned) and time.monotonic() < deadline:
                    time.sleep(0.02)
                assert not any(present(pid) for pid in owned), f'{kind}: signal left a producer or descendant alive'
                assert not accepted.exists(), 'Interrupted producer published an acceptance receipt'
        finally:
            # Own only the fixture child and its descendants. Baseline failures
            # must not leave a process behind.
            if owned and present(owned[0]):
                os.kill(owned[0], signal.SIGTERM)
            if process and process.poll() is None:
                process.kill(); process.wait()
            deadline = time.monotonic() + 3
            while any(present(pid) for pid in owned) and time.monotonic() < deadline:
                time.sleep(0.02)
            for pid in owned:
                if present(pid): os.kill(pid, signal.SIGKILL)
# Every mutating entrypoint must opt in. Merely importing a library does not
# install process-wide signal policy.
for path in [*cross.glob('*.py'), *FILES.glob('*.py')]:
    source = ast.parse(path.read_text())
    main = [n for n in source.body if isinstance(n, ast.If) and '__name__' in ast.unparse(n.test)]
    if main:
        assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'install_signal_handlers' for node in main for n in ast.walk(node)), str(path)
print('PASS: TERM/HUP drain actual fetch and CMake-install CLI descendants; all mutating entrypoints opt in')
