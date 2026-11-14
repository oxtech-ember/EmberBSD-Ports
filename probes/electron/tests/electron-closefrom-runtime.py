#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Causal inherited-socket EOF check using an actual sandboxed Electron renderer."""
import argparse
import errno
import fcntl
import json
import math
import os
from pathlib import Path
import selectors
import signal
import socket
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--electron', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True, help='new result directory')
parser.add_argument('--expected-electron', required=True)
parser.add_argument('--timeout', type=float, default=30)
args = parser.parse_args()
if os.geteuid() == 0:
    parser.error('run as an unprivileged user with the selected desktop environment')
if not args.electron.is_absolute() or not args.electron.is_file() or not math.isfinite(args.timeout) or args.timeout <= 0:
    parser.error('select an absolute executable and a positive timeout')
args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
script = Path(__file__).resolve().with_suffix('.cjs')
fds = (171, 300)
peers = []
child_ends = []
process = None
result = {'passed': False, 'electron': str(args.electron), 'expected': args.expected_electron, 'fds': list(fds)}

def validate_renderer_pid(main, renderer):
    if type(renderer) is not int or renderer <= 0 or renderer == main:
        raise RuntimeError('renderer PID must identify a separate process')


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False

def group_gone(pgid):
    try:
        os.killpg(pgid, 0)
        return False
    except ProcessLookupError:
        return True
    except PermissionError:
        return False

try:
    for fd in fds:
        peer, child = socket.socketpair()
        peers.append(peer)
        try:
            reserved = fcntl.fcntl(child.fileno(), fcntl.F_DUPFD, fd)
        finally:
            child.close()
        if reserved != fd:
            os.close(reserved)
            raise RuntimeError('required descriptor already in use: ' + str(fd))
        child_ends.append(reserved)
        os.set_inheritable(reserved, True)
    log = (args.output / 'stderr.log').open('wb')
    try:
        process = subprocess.Popen([str(args.electron), str(script), *(str(fd) for fd in fds), args.expected_electron],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                   pass_fds=fds, start_new_session=True, env=os.environ.copy())
        if os.getpgid(process.pid) != process.pid:
            raise RuntimeError('unexpected process group')
        for fd in child_ends:
            os.close(fd)
        child_ends.clear()
        selector = selectors.DefaultSelector()
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
        stdout_log = (args.output / 'stdout.log').open('wb')
        buffer = bytearray()
        deadline = time.monotonic() + args.timeout
        def read_record(phase):
            while True:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Electron ' + phase + ' timeout')
                newline = buffer.find(b'\n')
                if newline > 65536:
                    raise RuntimeError('stdout line exceeds limit')
                if newline >= 0:
                    line = bytes(buffer[:newline]); del buffer[:newline + 1]
                    if not line.startswith(b'EMBER_QA '):
                        continue
                    record = json.loads(line[len(b'EMBER_QA '):])
                    if record.get('phase') != phase:
                        raise RuntimeError('unexpected record phase')
                    return record
                if len(buffer) > 65536:
                    raise RuntimeError('stdout line exceeds limit')
                events = selector.select(max(0, deadline - time.monotonic()))
                if not events:
                    raise TimeoutError('Electron ' + phase + ' timeout')
                chunk = os.read(process.stdout.fileno(), 4096)
                if not chunk:
                    raise RuntimeError('Electron stdout closed before ' + phase)
                stdout_log.write(chunk); stdout_log.flush(); buffer.extend(chunk)
                if stdout_log.tell() > 1024 * 1024:
                    raise RuntimeError('stdout exceeds total limit')
        ready = read_record('ready')
        if ready.get('mainPID') != process.pid or ready.get('fds') != list(fds) or ready.get('electron') != args.expected_electron:
            raise RuntimeError('unexpected readiness record')
        renderer = ready.get('rendererPID')
        validate_renderer_pid(process.pid, renderer)
        result.update(ready=ready, renderer_distinct_from_main=True)
        selector.unregister(process.stdout)
        for peer in peers:
            peer.setblocking(False)
            selector.register(peer, selectors.EVENT_READ, peer.fileno())
        eofs = []
        while len(eofs) < len(peers):
            events = selector.select(max(0, deadline - time.monotonic()))
            if not events:
                raise TimeoutError('inherited socket EOF timeout')
            for key, _ in events:
                data = key.fileobj.recv(1)
                if data:
                    raise RuntimeError('unexpected socket data')
                eofs.append(key.data)
                selector.unregister(key.fileobj)
        if process.poll() is not None or not alive(process.pid) or not alive(renderer):
            raise RuntimeError('Electron main or renderer exited before EOF proof')
        result.update(ready=ready, peer_eof_count=len(eofs), main_alive_at_eof=True, renderer_alive_at_eof=True)
        selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
        process.stdin.write(b'prove\n'); process.stdin.flush()
        proof = read_record('proof')
        if proof.get('mainPID') != process.pid or proof.get('rendererPID') != renderer or proof.get('value') is not True or process.poll() is not None:
            raise RuntimeError('renderer proof differs or process exited')
        result['renderer_proof'] = proof
        process.stdin.write(b'quit\n')
        process.stdin.flush()
        process.stdin.close()
        code = process.wait(timeout=args.timeout)
        if code != 0:
            raise RuntimeError('normal app.quit exit status: ' + str(code))
        end = time.monotonic() + args.timeout
        while not group_gone(process.pid):
            if time.monotonic() >= end:
                raise TimeoutError('owned process group survived normal exit')
            time.sleep(0.05)
        result.update(normal_exit=code, owned_group_gone=True, passed=True)
    finally:
        if 'stdout_log' in locals():
            stdout_log.close()
        log.close()
except Exception as exc:
    result['error'] = repr(exc)
finally:
    for fd in child_ends:
        os.close(fd)
    for peer in peers:
        peer.close()
    if process is not None and not result['passed']:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            result['cleanup_error'] = 'cannot signal owned process group'
        end = time.monotonic() + 5
        while time.monotonic() < end:
            process.poll()
            if group_gone(process.pid):
                break
            time.sleep(0.05)
        if not group_gone(process.pid):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                result['cleanup_error'] = 'cannot kill owned process group'
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            result['cleanup_error'] = 'main survived SIGKILL'
        end = time.monotonic() + 5
        while not group_gone(process.pid) and time.monotonic() < end:
            time.sleep(0.05)
        if not group_gone(process.pid):
            result['cleanup_error'] = 'owned process group survived cleanup'
    (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
raise SystemExit(0 if result['passed'] else 1)
