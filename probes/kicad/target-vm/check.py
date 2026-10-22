#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check real target identity, argv and transport.
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile
from vm import canonical, command_log, entrypoint, parser, sdk, write


def main():
    args = parser(__doc__, ['work', 'target_query_py', 'readelf']).parse_args()
    inventory, jsonio, paths, process, identity_api = sdk(args.sdk_source)
    work, launcher, readelf = map(canonical, [args.work, args.target_query_py, args.readelf])
    source = jsonio.read_json(str(work / 'artifacts/input.json'))
    ssh = [work / 'bin/ssh', 'ember-e14-query']
    receipts = []
    logs = Path(tempfile.mkdtemp(prefix='acceptance-', dir=work / 'logs'))
    def run(name, expected, *command, env=None):
        output = command_log(work, name, expected, command, env=env, log_directory=logs)
        receipts.append(dict(name=name, exit=expected, expected=expected))
        return output
    output = run('identity', 0, *ssh, '''set -eu
 test "$(uname -s)" = NetBSD
 test "$(uname -p)" = aarch64
 test "$HOME" = /root
 test "$USER" = root
 test "$(id -u)" = 0
 test "$(getent group tty)" = 'tty:*:4:root'
 test -c /dev/ptmx
 test -d /usr/lib/i18n
 test -d /usr/share/i18n
 test -d /usr/share/locale
 test ! -e /usr/bin/gcc
 test ! -e /usr/bin/cc
 test ! -e /usr/pkg/bin/gcc
 uname -a
 id
 locale -a
 /sbin/mount
 df -ki /
''')
    if b'on /dev/pts type ptyfs' not in output:
        raise ValueError('ptyfs not mounted')
    import re
    libc = next((name for name in source['sources_sha256'] if re.search(r'/lib/libc\.so\.\d+\.\d+$', name)), None)
    if libc is None:
        raise ValueError('base libc inventory missing')
    relatives = ['/bin/sh', '/usr/bin/uname', '/usr/bin/sha256', '/usr/sbin/sshd', '/sbin/chown', '/usr/sbin/chown', '/usr/bin/chgrp', libc.removeprefix(source['base'])]
    for relative in relatives:
        original = source['base'] + relative
        expected = source['sources_sha256'][original]
        if isinstance(expected, dict):
            alias = Path(original)
            if not alias.is_symlink() or os.readlink(alias) != expected.get('symlink'):
                raise ValueError(f'unverified base alias: {original}')
            target = expected['symlink']
            if relative not in ('/usr/sbin/chown', '/usr/bin/chgrp') or target != '/sbin/chown':
                raise ValueError('Unexpected selected base command alias.')
            original = source['base'] + target
            expected = source['sources_sha256'].get(original)
        if not isinstance(expected, str) or inventory.sha256_file(original) != expected:
            raise ValueError(f'unverified base source: {original}')
        actual = run('hash-' + Path(relative).name + '-' + str(len(receipts)), 0, *ssh, 'sha256 -q ' + shlex.quote(relative)).decode().strip()
        if actual != expected:
            raise ValueError(f'guest base differs: {relative}')
    run('package-directory-ownership', 0, *ssh, '''set -eu
 probe=$(mktemp /tmp/e14-ownership.XXXXXXXX)
 trap 'rm -f "$probe"' EXIT HUP INT TERM
 /usr/sbin/chown root "$probe"
 /usr/bin/chgrp wheel "$probe"
''')
    if b'/dev/pts/' not in run('pty', 0, work / 'bin/ssh', '-tt', 'ember-e14-query', 'test -t 0 && tty && stty -a'):
        raise ValueError('real target PTY missing')
    run('status37', 37, *ssh, 'exit 37')
    if b'UNREACHED' in run('set-e-failure', 1, *ssh, "sh -c 'set -e; false; echo UNREACHED'"):
        raise ValueError('shell failure was hidden')
    wrong_hosts = work / 'keys' / ('wrong_known_hosts-' + logs.name)
    key_type, key_data = (work / 'keys/client.pub').read_text().split()[:2]
    write(wrong_hosts, f'ember-e14-query {key_type} {key_data}\n')
    run('wrong-host', 255, work / 'bin/ssh', '-o', 'UserKnownHostsFile=' + str(wrong_hosts), 'ember-e14-query', 'true')
    shell = work / 'probes/sh'
    shutil.copyfile(Path(source['base']) / 'bin/sh', shell)
    shell.chmod(0o755)
    config = logs / 'query-check.json'
    jsonio.write_json(str(config), dict(target='aarch64', build_root=str(work / 'probes'), sysroot=source['base'],
                      cache=str(work / 'cache'), readelf=str(readelf), ssh='ember-e14-query', library_dirs=[]), mode=0o600)
    env = dict(os.environ, EMBERBSD_GI_QUERY_CONFIG=str(config), PATH=str(work / 'bin') + ':' + os.environ['PATH'],
               EMBERBSD_GI_PYTHON=sys.executable, EMBERBSD_SDK_SOURCE=str(args.sdk_source.resolve()),
               EMBERBSD_GI_FAILURE_MARKER=str(work / 'probes/transport-failed'))
    if Path(env['EMBERBSD_GI_FAILURE_MARKER']).exists():
        raise ValueError('an earlier transport failure needs review')
    run('query-config', 0, sys.executable, launcher, '--check', work / 'probes', source['base'], readelf, env=env)
    values = ['two words', "single'quote", 'double"quote', '', '$(touch /tmp/ember-query-injection)', '; exit 99']
    body = f'test "$#" = {len(values)} || exit 41\n'
    for value in values:
        body += f'test "$1" = {shlex.quote(value)} || exit 42\nshift\n'
    body += "printf '%s\\n' ARGV_OK\nexit 37\n"
    output = run('query-literal-argv', 37, sys.executable, launcher, '--execute', shell, '-c', body, 'query', *values, env=env)
    if output != b'ARGV_OK\n':
        raise ValueError('literal argv oracle failed')
    run('query-success', 0, sys.executable, launcher, '--execute', shell, '-c', 'printf TARGET_OK', env=env)
    run('query-negative', 1, sys.executable, launcher, '--execute', shell, '-c', 'false', env=env)
    if Path(env['EMBERBSD_GI_FAILURE_MARKER']).exists():
        raise ValueError('legitimate target status became a transport failure')
    no_marker = {key: value for key, value in env.items() if key != 'EMBERBSD_GI_FAILURE_MARKER'}
    run('dump-args-still-rejected', 1, sys.executable, launcher, shell, 'literal', env=no_marker)
    if b'only an optional introspect-dump' not in (logs / 'check-dump-args-still-rejected.log').read_bytes():
        raise ValueError('dump mode unexpectedly accepted literal args')
    run('cleanup', 0, *ssh, '''set -eu
 test ! -e /tmp/ember-query-injection
 for path in /tmp/ember-gir.*; do test ! -e "$path"; done
''')
    capacity = run('capacity', 0, *ssh, 'df -ki /')
    data = next((line.split() for line in capacity.decode().splitlines() if line.startswith('/dev/ld4a')), [])
    if len(data) < 8 or int(data[6]) < 16000:
        raise ValueError('insufficient free target inodes')
    jsonio.write_json(str(work / 'artifacts/acceptance.json'), dict(checks=receipts, free_kib=int(data[3]), free_inodes=int(data[6]),
        launcher_sha256=inventory.sha256_file(launcher), logs=str(logs), allocated_disk_bytes=(work / 'query.ffs').stat().st_blocks * 512), exclusive=False)
    print('PASS: real EmberBSD SSH, PTY, literal query argv, status, provider hashes and cleanup')


if __name__ == '__main__':
    entrypoint(main)
