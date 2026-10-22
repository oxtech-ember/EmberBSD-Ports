#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Halt only the recorded private guest.
import subprocess
import time
from vm import canonical, entrypoint, owned_identity, parser, sdk


class HaltTimeout(ValueError):
    """Keep bounded SSH diagnostics while leaving QEMU untouched."""
    def __init__(self, message, stdout=b'', stderr=b''):
        super().__init__(message)
        self.stdout = stdout or b''
        self.stderr = stderr or b''


def ssh_halt(command, deadline, *, clock=time.monotonic, popen=subprocess.Popen):
    """Bound the owned SSH client and its pipes. Never signal the guest."""
    child = popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    def wait(cap):
        remaining = deadline - clock()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, 0)
        return child.communicate(timeout=min(cap, remaining))
    try:
        out, err = wait(35)
    except subprocess.TimeoutExpired as initial:
        out, err = initial.stdout or b'', initial.stderr or b''
        try:
            child.terminate()
        except ProcessLookupError:
            pass
        try:
            out, err = wait(5)
        except subprocess.TimeoutExpired as terminated:
            out, err = terminated.stdout or out, terminated.stderr or err
            try:
                child.kill()
            except ProcessLookupError:
                pass
            try:
                out, err = wait(5)
            except subprocess.TimeoutExpired as killed:
                raise HaltTimeout('owned SSH pipes did not close after kill; QEMU retained',
                                  killed.stdout or out, killed.stderr or err)
        raise HaltTimeout('owned SSH halt request timed out; QEMU retained', out, err)
    return child.returncode, out, err


def main():
    args = parser(__doc__, ['work']).parse_args()
    inventory, jsonio, paths, process, identity = sdk(args.sdk_source)
    work = canonical(args.work)
    record = jsonio.read_json(str(work / 'artifacts/run.json'))
    if inventory.sha256_file(record['argv'][0]) != record['qemu_sha256']:
        raise ValueError('QEMU executable changed since launch')
    pid, current = owned_identity(work, record, identity)
    if current is None:
        raise ValueError('recorded runner is absent; inspect its console log')
    acknowledgment = b'EMBER_QUERY_HALT_REQUEST_ACCEPTED'
    deadline = time.monotonic() + 45
    # Only the owned SSH client is killed on timeout. QEMU is never signalled.
    command = [str(work / 'bin/ssh'), 'ember-e14-query',
               "set -eu; printf '%s\\n' EMBER_QUERY_HALT_REQUEST_ACCEPTED; sync; /sbin/halt -p"]
    try:
        ssh_exit, out, err = ssh_halt(command, deadline)
    except HaltTimeout as error:
        (work / 'logs/stop.log').write_bytes(b'ssh_timeout=true\n' + str(error).encode() + b'\n' + error.stdout + error.stderr)
        raise
    (work / 'logs/stop.log').write_bytes(f'ssh_exit={ssh_exit}\n'.encode() + out + err)
    if acknowledgment not in out.splitlines():
        raise ValueError('guest did not acknowledge the halt request')
    while True:
        _, current = owned_identity(work, record, identity)
        if current is None:
            break
        if time.monotonic() >= deadline:
            raise ValueError('graceful halt timed out; guest retained for inspection')
        time.sleep(.25)
    jsonio.write_json(str(work / 'artifacts/stopped.json'), dict(pid=pid, ssh_exit=ssh_exit,
                      halt_request_acknowledged=True, recorded_process_exited=True), exclusive=False)
    print('The guest acknowledged the halt request and the recorded process exited.')


if __name__ == '__main__':
    entrypoint(main)
