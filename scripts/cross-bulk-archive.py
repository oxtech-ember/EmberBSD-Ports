#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors.
"""Check runtime metadata when reusing an ordinary source-built archive."""
import argparse
from pathlib import Path
import subprocess
import sys


def manifest(raw):
    name = None
    deps = []
    for line in raw.splitlines():
        if line.startswith(b'@name '):
            if name is not None:
                raise ValueError('duplicate package identity')
            name = line[6:]
        elif line.startswith(b'@pkgdep '):
            deps.append(line[8:])
    if not name:
        raise ValueError('missing package identity')
    return name, sorted(deps), raw


def validate(archive, name, resolved, pkg_info):
    expected = []
    for row in resolved.read_bytes().splitlines():
        fields = row.split()
        if len(fields) != 3:
            raise ValueError('invalid resolved dependency row')
        if fields[0] == b'full':
            expected.append(fields[1])
    # pkg_info handles the configured compression and signed pkgsrc archives.
    # Keep pkgdb and archive as independent evidence.
    def read(ref):
        return manifest(subprocess.check_output([*pkg_info, '-q', '-f', ref]))
    archived = read(str(archive))
    if archived[:2] != (name.encode(), sorted(expected)):
        raise ValueError('archive differs from expected runtime requirements')
    if archived != read(name):
        raise ValueError('installed package differs from archive')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('name')
    parser.add_argument('resolved', type=Path)
    parser.add_argument('pkg_info', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if not args.pkg_info:
            raise ValueError('missing selected pkg_info')
        validate(args.archive, args.name, args.resolved, args.pkg_info)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
