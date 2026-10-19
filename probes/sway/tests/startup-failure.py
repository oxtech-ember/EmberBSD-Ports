#!/usr/bin/env python3
"""Require controlled Sway startup failure for invalid IPC socket paths."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import uuid

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--host', required=True)
p.add_argument('--sway', default='/usr/pkg/bin/sway')
p.add_argument('--results', type=Path, required=True)
a = p.parse_args()
assert a.sway.startswith('/') and a.results.is_absolute() and not a.results.exists()
a.results.mkdir(parents=True)
remote = '/tmp/sway-startup-' + uuid.uuid4().hex
records = []
cleanup_error = None
removed = False

def ssh(command, data=None, timeout=40):
    return subprocess.run(['ssh', '-o', 'ConnectTimeout=15', a.host, command],
                          input=data, capture_output=True, timeout=timeout)

def checked(command, data=None):
    r = ssh(command, data)
    assert r.returncode == 0, (command, r.stderr)
    return r.stdout

identity = checked('uname -srm; id -u nobody; id -g nobody').decode().splitlines()
assert identity[0].startswith('NetBSD ')
uid, gid = map(int, identity[1:])
checked('umask 077; mkdir ' + shlex.quote(remote))
try:
    checked('mkdir ' + shlex.quote(remote + '/runtime'))
    checked('cat > ' + shlex.quote(remote + '/config'), b'output * mode 640x480\n')
    checked('cat > ' + shlex.quote(remote + '/blocked'), b'not a directory\n')
    checked(shlex.join(['/usr/sbin/chown', '-R', f'{uid}:{gid}', remote]))
    for case in ('missing', 'blocked'):
        # Both paths fit sun_path. Their parent cannot hold an IPC socket.
        invalid = remote + '/' + case + '/ipc.sock'
        command = shlex.join(['env', 'PATH=/usr/pkg/bin:/usr/bin:/bin',
            'HOME=' + remote, 'XDG_CONFIG_HOME=' + remote,
            'XDG_RUNTIME_DIR=' + remote + '/runtime', 'SWAYSOCK=' + invalid,
            'WLR_BACKENDS=headless', 'WLR_HEADLESS_OUTPUTS=1',
            'WLR_LIBINPUT_NO_DEVICES=1', 'WLR_RENDERER=pixman',
            a.sway, '--debug', '--config', remote + '/config'])
        # A waiting parent records the compositor status, including signals.
        # SSH can otherwise translate a signalled remote command to status 255.
        script = ('ulimit -c 0; ' + command + ' </dev/null & child=$!; '
                  'printf "%s\\n" "$child" >' + shlex.quote(remote + '/pid') +
                  '; wait "$child"; status=$?; printf "%s\\n" "$status" >' +
                  shlex.quote(remote + '/status') + '; exit 0')
        result = ssh(shlex.join(['su', '-m', 'nobody', '-c', script]))
        (a.results / (case + '.stdout')).write_bytes(result.stdout)
        (a.results / (case + '.stderr')).write_bytes(result.stderr)
        assert result.returncode == 0, ('SSH/supervisor failure', result.stderr)
        status = int(checked('cat ' + shlex.quote(remote + '/status')))
        records.append(dict(case=case, status=status, ssh_status=result.returncode,
                            ipc_bind_error=b'Unable to bind IPC socket' in result.stderr))
    assert all(r['status'] == 1 and r['ipc_bind_error'] for r in records), records
    assert checked('find ' + shlex.quote(remote + '/runtime') + ' -type s') == b''
finally:
    try:
        pid = int(checked('cat ' + shlex.quote(remote + '/pid')))
        assert pid > 1
        state = ssh(shlex.join(['ps', '-p', str(pid), '-o', 'pid=',
                               '-o', 'uid=', '-o', 'command=']))
        assert state.returncode in (0, 1), state.stderr
        if state.stdout.strip():
            fields = state.stdout.decode().split(None, 2)
            assert len(fields) == 3 and int(fields[0]) == pid and int(fields[1]) == uid
            assert remote + '/config' in fields[2], 'Refuse to stop a different process'
            checked(shlex.join(['kill', '-TERM', str(pid)]))
            raise AssertionError('Startup failure left a running compositor; sent TERM')
        checked('rm -rf ' + shlex.quote(remote) + '; test ! -e ' + shlex.quote(remote))
        removed = True
    except BaseException as error:
        cleanup_error = repr(error)
    (a.results / 'receipt.json').write_text(json.dumps(dict(target=identity[0],
        sway=a.sway, cases=records, cleanup_error=cleanup_error,
        remote_work_removed=removed), indent=2) + '\n')
    assert cleanup_error is None, cleanup_error
print('PASS: missing and non-directory SWAYSOCK parents return startup error 1 without a signal')
