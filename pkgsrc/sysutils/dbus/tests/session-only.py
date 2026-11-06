#!/usr/bin/env python3
# Copyright (c) 2026 EmberBSD contributors
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the installed session-only DBus package without a system bus."""
import argparse
import os
import platform
from pathlib import Path
import time
import socket
import subprocess
import tempfile
import threading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, required=True,
                        help='disposable prefix installed by the SDK owner')
    parser.add_argument('--producer-prefix', type=Path, required=True,
                        help='existing original prefix, kept present for relocation checks')
    args = parser.parse_args()
    if platform.system() != 'Darwin':
        raise ValueError('this fixture uses Darwin DYLD library tracing')
    root = args.prefix.resolve(strict=True)
    producer = args.producer_prefix.resolve(strict=True)
    if root == producer:
        raise ValueError('the installed and producer prefixes must differ')
    env = os.environ.copy()
    for key in ('DBUS_SESSION_BUS_ADDRESS', 'DBUS_SYSTEM_BUS_ADDRESS',
                'DBUS_STARTER_ADDRESS', 'DBUS_STARTER_BUS_TYPE', 'DISPLAY',
                'DYLD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES', 'LD_LIBRARY_PATH', 'LD_PRELOAD'):
        env.pop(key, None)
    env['PATH'] = str(root / 'bin') + ':/usr/bin:/bin'
    assert not (root / 'share/dbus-1/system.conf').exists()
    assert not (root / 'libexec/dbus-daemon-launch-helper').exists()
    machine_id = root / 'var/lib/dbus/machine-id'
    before = machine_id.read_bytes()

    def run(command, *, extra_env=None):
        selected = dict(env, **(extra_env or {}))
        return subprocess.run([str(x) for x in command], env=selected, text=True,
                              capture_output=True, timeout=20, check=False)

    with tempfile.TemporaryDirectory(prefix='dbus13-', dir='/tmp') as directory:
        work = Path(directory); runtime = work / 'runtime'; runtime.mkdir(mode=0o700)
        data = work / 'data'; services = data / 'dbus-1/services'; services.mkdir(parents=True)
        env['XDG_RUNTIME_DIR'] = str(runtime); env['XDG_DATA_HOME'] = str(data)
        env['XDG_DATA_DIRS'] = str(data)
        wrapper = work / 'service.sh'; pidfile = work / 'service.pid'
        name = 'org.emberbsd.SessionProbe'
        wrapper.write_text('#!/bin/sh\nprintf "%s" "$$" > "' + str(pidfile) +
                           '"\nexec "' + str(root / 'bin/dbus-test-tool') +
                           '" echo --name=' + name + '\n')
        wrapper.chmod(0o755)
        (services / (name + '.service')).write_text(
            '[D-BUS Service]\nName=' + name + '\nExec=' + str(wrapper) + '\n')
        try:
            result = run([root / 'bin/dbus-run-session', '--', root / 'bin/dbus-send',
                          '--session', '--print-reply', '--dest=' + name,
                          '/org/emberbsd/Probe', 'org.emberbsd.Probe.Ping'])
            assert result.returncode == 0 and pidfile.exists(), (result.stdout, result.stderr)
            print('private session service activation PASS', flush=True)
            result = run([root / 'bin/dbus-uuidgen', '--get'],
                         extra_env={'DYLD_PRINT_LIBRARIES': '1'})
            assert result.returncode == 0 and str(root / 'lib/libdbus-1.3.dylib') in result.stderr
            print('installed libdbus loaded without a loader override PASS', flush=True)
            result = run([root / 'bin/dbus-daemon', '--system', '--nofork'])
            assert result.returncode != 0 and 'system.conf' in result.stderr, result.stderr
            print('system daemon without packaged config fails closed PASS', flush=True)
            result = run([root / 'bin/dbus-uuidgen', '--ensure'])
            assert result.returncode == 0 and machine_id.read_bytes() == before
            print('machine-id ensure repeat PASS', flush=True)
            path = str(work / 'system.sock'); listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(path); listener.listen(1); listener.settimeout(8); hits = []
            def accept():
                try:
                    conn, _ = listener.accept(); hits.append(True); conn.close()
                except (OSError, TimeoutError):
                    pass
            thread = threading.Thread(target=accept, daemon=True); thread.start()
            result = run([root / 'bin/dbus-send', '--system', '--print-reply',
                          '--dest=org.freedesktop.DBus', '/org/freedesktop/DBus',
                          'org.freedesktop.DBus.ListNames'],
                         extra_env={'DBUS_SYSTEM_BUS_ADDRESS': 'unix:path=' + path})
            thread.join(timeout=10); listener.close(); assert hits, result.stderr
            print('explicit external system address PASS', flush=True)
        finally:
            if pidfile.exists():
                pid = int(pidfile.read_text())
                deadline = time.monotonic() + 10
                while True:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    if time.monotonic() >= deadline:
                        raise RuntimeError('activated service did not exit after bus shutdown')
                    time.sleep(0.1)


if __name__ == '__main__':
    main()
