#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare and verify the pinned shared littlefs source."""
import hashlib
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS / 'scripts/source-inputs/common'))
from network_archive import NetworkOwner


class Owner(NetworkOwner):
    def __init__(self):
        super().__init__(__file__, 'devel/littlefs', '', 'littlefs', '.tar.gz', 'littlefs-')

    def recipe(self, exported):
        root = Path(exported) / self.PACKAGE
        makefile = self.read(root / 'Makefile').decode('utf-8')

        def field(name, pattern):
            values = re.findall(r'^[ \t]*' + name + r'[ \t]*=[ \t]*(' + pattern + r')[ \t]*$',
                                makefile, re.M)
            self.require(len(values) == 1, self.PACKAGE + ': ambiguous ' + name)
            return values[0]

        distname = field('DISTNAME', r'littlefs-[0-9]+(?:\.[0-9]+)+')
        tag = field('GITHUB_TAG', r'refs/tags/v[0-9]+(?:\.[0-9]+)+')
        self.require(tag == 'refs/tags/v' + distname.removeprefix('littlefs-'),
                     self.PACKAGE + ': release tag and source version differ')
        archive = distname + '.tar.gz'
        info = self.read(root / 'distinfo').decode('utf-8')
        hashes = {}
        for label, key in (('SHA512', 'sha512'), ('BLAKE2s', 'blake2s'), ('Size', 'size')):
            values = re.findall(r'^' + label + r' \(' + re.escape(archive) +
                                r'\) = (\S+)(?: bytes)?$', info, re.M)
            self.require(len(values) == 1, self.PACKAGE + ': ambiguous archive ' + label)
            hashes[key] = int(values[0]) if key == 'size' else values[0]
        declared = re.findall(r'^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$', info, re.M)
        patches_dir = root / 'patches'
        patches = sorted(patches_dir.glob('patch-*')) if patches_dir.exists() else []
        self.require([path.name for path in patches] == sorted(name for name, _ in declared),
                     self.PACKAGE + ': patch inventory differs from distinfo')
        for name, expected in declared:
            data = self.read(patches_dir / name)
            filtered = b''.join(line for line in data.splitlines(keepends=True)
                                if b'$NetBSD' not in line)
            self.require(hashlib.sha1(filtered).hexdigest() == expected,
                         self.PACKAGE + ': patch checksum differs: ' + name)
        inputs = [root / 'Makefile', root / 'DESCR', root / 'distinfo', *patches]
        return (dict(distname=distname, archive=archive,
                     archive_root='littlefs-' + tag.rsplit('/', 1)[1][1:], **hashes,
                     recipe={str(path.relative_to(root)): self.digest(self.read(path))
                             for path in inputs}), patches)


if __name__ == '__main__':
    Owner().main()
