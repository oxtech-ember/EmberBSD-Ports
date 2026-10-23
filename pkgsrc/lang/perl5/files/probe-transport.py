#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Bound upstream Perl Configure transport.
"""Copy and run Configure probes. Keep feature failures distinct from transport."""
import argparse
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
import time


class TransportError(Exception):
    pass


def scoped(root, value):
    path = PurePosixPath(value)
    if '..' in path.parts:
        raise TransportError('parent traversal in probe path')
    path = path if path.is_absolute() else root / path
    if not path.is_relative_to(root):
        raise TransportError('probe path is outside target directory')
    return path


def invoke(argv, timeout, *, probe=False):
    try:
        result = subprocess.run(argv, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise TransportError(str(error)) from error
    if result.returncode < 0 or result.returncode == 255 or (result.returncode and not probe):
        raise TransportError(f'transport command failed with status {result.returncode}')
    return result.returncode


def execute(args):
    root = PurePosixPath(args.directory)
    if not root.is_absolute() or root == PurePosixPath('/') or '..' in root.parts:
        raise TransportError('target directory must be an absolute private directory')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', args.host) or not re.fullmatch(r'[A-Za-z0-9_-]+', args.user):
        raise TransportError('invalid SSH host or user')
    if not 1 <= args.port <= 65535 or not 1 <= args.timeout <= 300:
        raise TransportError('invalid SSH port or deadline')
    if args.failure.exists():
        raise TransportError('an earlier transport command failed')
    options = ['-oBatchMode=yes', '-oConnectTimeout=10', '-oServerAliveInterval=5', '-oServerAliveCountMax=2']
    peer = args.user + '@' + args.host
    deadline = time.monotonic() + args.timeout

    def bounded(argv, probe=False):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TransportError('probe transport deadline expired')
        return invoke(argv, remaining, probe=probe)

    def remote(command, probe=False):
        return bounded(['ssh', *options, '-p', str(args.port), peer, command], probe=probe)

    def transfer(value, receive=False):
        path = scoped(root, value)
        local = Path(value)
        if local.is_absolute() or '..' in local.parts:
            raise TransportError('local probe paths must be relative')
        if receive:
            if local.is_symlink() or (local.exists() and not local.is_file()):
                raise TransportError('probe output must be a regular file')
            source, dest = peer + ':' + shlex.quote(str(path)), str(local)
        else:
            if not local.is_file() or local.is_symlink():
                raise TransportError('probe input must be a regular file')
            remote('mkdir -p ' + shlex.quote(str(path.parent)))
            source, dest = str(local), peer + ':' + shlex.quote(str(path))
        bounded(['scp', '-O', *options, '-P', str(args.port), source, dest])

    values = args.values
    if args.operation in ('to', 'from'):
        for value in values:
            transfer(value, args.operation == 'from')
        return 0
    if args.operation == 'mkdir':
        for value in values:
            remote('mkdir -p ' + shlex.quote(str(scoped(root, value))))
        return 0
    # Configure uses simple executable paths, numeric arguments, and this one
    # pipeline for stdin/fflush tests. Its fixture files are copied explicitly.
    if not values:
        raise TransportError('missing probe executable')
    if len(values) == 1 and values[0].strip() == 'cat tryp.c | ./tryp':
        command = 'cat tryp.c | ./tryp'
    else:
        if not re.fullmatch(r'\./[A-Za-z0-9_.-]+', values[0]):
            raise TransportError('unsupported probe executable')
        transfer(values[0])
        command = shlex.join(values)
    return remote('cd ' + shlex.quote(str(root)) + ' && ' + command, probe=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('host', 'user', 'directory'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--port', type=int, default=22)
    parser.add_argument('--timeout', type=int, default=60)
    parser.add_argument('--failure', type=Path, required=True)
    parser.add_argument('operation', choices=('run', 'to', 'from', 'mkdir'))
    parser.add_argument('values', nargs='*')
    args = parser.parse_args()
    try:
        return execute(args)
    except TransportError as error:
        try:
            with args.failure.open('x') as stream:
                stream.write(str(error) + '\n')
        except FileExistsError:
            pass
        print('Perl probe transport: ' + str(error), file=sys.stderr)
        return 255


if __name__ == '__main__':
    sys.exit(main())
