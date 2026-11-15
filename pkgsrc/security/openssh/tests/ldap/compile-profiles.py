#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compile OpenSSH target sources with LDAP and builtin-crypto selections."""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'os-source', 'nbmake', 'source',
             'sysroot', 'builtin-config-object', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--ldap-sysroot', type=Path)
parser.add_argument('--config-object', type=Path)
parser.add_argument('--builtin-only', action='store_true',
                    help='run only the builtin-crypto ssh-keygen check')
args = parser.parse_args()
assert all(value is None or not isinstance(value, Path) or value.is_absolute()
           for value in vars(args).values())
if not args.builtin_only and (args.ldap_sysroot is None or args.config_object is None):
    parser.error('--ldap-sysroot and --config-object are required unless --builtin-only is set')
args.work_dir.mkdir(parents=True, exist_ok=True)
runner = [sys.executable, '-B', str(args.sdk_source / 'scripts/run-native-os.py'),
          '--host-prefix', str(args.host_prefix), '--source', str(args.os_source),
          '--routing', str(args.work_dir / 'native-routing'), '--cwd', str(args.os_source),
          '--capture', '--shell', '--', str(args.nbmake)]
commands = []
for enabled in (() if args.builtin_only else (False, True)):
    policy = 'yes' if enabled else 'no'
    root = args.ldap_sysroot if enabled else args.sysroot
    query = runner + ['-C', str(args.os_source / 'crypto/external/bsd/openssh/libexec/sshd-session'),
        'MKLDAP=' + policy, 'USE_LDAP=' + policy, 'DESTDIR=' + str(root),
        'OPENSSH_CONFIG_OBJECT=' + str(args.config_object),
        'EMBER_OPENSSH_SOURCE=' + str(args.source), '-V', '${CC} ${CPPFLAGS} ${CFLAGS} ${COPTS.sshd-session.c}']
    result = subprocess.run(query, check=True, capture_output=True, text=True)
    command = shlex.split(result.stdout) + ['-fsyntax-only', str(args.source / 'sshd-session.c')]
    assert any(word == '-DWITH_NETBSD_LPK' for word in command) == enabled
    commands.append(command)
    (args.work_dir / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    subprocess.run(command, cwd=args.work_dir, check=True)
    print('PASS: sshd-session MKLDAP=' + policy, flush=True)

query = runner + ['-C', str(args.os_source / 'crypto/external/bsd/openssh/bin/ssh-keygen'),
    'EMBER_OPENSSH_CRYPTO=builtin', 'MKPIC=no', 'MKLDAP=no', 'USE_LDAP=no',
    'DESTDIR=' + str(args.sysroot),
    'OPENSSH_CONFIG_OBJECT=' + str(args.builtin_config_object),
    'EMBER_OPENSSH_SOURCE=' + str(args.source), '-V',
    '${CC} ${CPPFLAGS} ${CFLAGS} ${COPTS.ssh-keygen.c}']
result = subprocess.run(query, check=True, capture_output=True, text=True)
command = shlex.split(result.stdout) + ['-fsyntax-only', str(args.source / 'ssh-keygen.c')]
assert '-DWITH_OPENSSL' not in command
assert '-DWITH_NETBSD_LPK' not in command
config_header = args.builtin_config_object / 'build/config.h'
config = config_header.read_text()
assert not re.search(r'^#define\s+WITH_OPENSSL(?:\s|$)', config, re.M)
commands.append(command)
(args.work_dir / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
subprocess.run(command, cwd=args.work_dir, check=True)
print('PASS: ssh-keygen builtin crypto without LDAP', flush=True)
