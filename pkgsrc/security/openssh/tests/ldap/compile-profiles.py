#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compile the real sshd-session source with both native OS LDAP selections."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'os-source', 'nbmake', 'source', 'sysroot', 'ldap-sysroot', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
assert all(path.is_absolute() for path in vars(args).values())
args.work_dir.mkdir(parents=True, exist_ok=True)
runner = [sys.executable, '-B', str(args.sdk_source / 'scripts/run-native-os.py'),
          '--host-prefix', str(args.host_prefix), '--source', str(args.os_source),
          '--routing', str(args.work_dir / 'native-routing'), '--cwd', str(args.os_source),
          '--capture', '--shell', '--', str(args.nbmake)]
commands = []
for enabled in (False, True):
    policy = 'yes' if enabled else 'no'
    root = args.ldap_sysroot if enabled else args.sysroot
    query = runner + ['-C', str(args.os_source / 'crypto/external/bsd/openssh/libexec/sshd-session'),
        'MKLDAP=' + policy, 'USE_LDAP=' + policy, 'DESTDIR=' + str(root),
        'EMBER_OPENSSH_SOURCE=' + str(args.source), '-V', '${CC} ${CPPFLAGS} ${CFLAGS} ${COPTS.sshd-session.c}']
    result = subprocess.run(query, check=True, capture_output=True, text=True)
    command = shlex.split(result.stdout) + ['-fsyntax-only', str(args.source / 'sshd-session.c')]
    assert any(word == '-DWITH_NETBSD_LPK' for word in command) == enabled
    commands.append(command)
    (args.work_dir / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    subprocess.run(command, cwd=args.work_dir, check=True)
    print('PASS: sshd-session MKLDAP=' + policy, flush=True)
