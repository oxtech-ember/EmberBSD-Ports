#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Prepare the complete canonical SQLite source from its common Ports owner."""
import hashlib
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS/'scripts/source-inputs/common'))
from network_archive import NetworkOwner


class Owner(NetworkOwner):
    def __init__(self):
        super().__init__(__file__, 'databases/sqlite3', '', 'sqlite', '', '')

    def load_sdk(self, argv):
        args = super().load_sdk(argv)
        from emberbsd_sdk import archive_metadata
        if archive_metadata.ARCHIVE_METADATA_API != 1:
            raise self.SDKError('selected SDK lacks archive metadata API 1')
        if getattr(self.sourceprep, 'ZIP_ARCHIVE_API', None) != 1:
            raise self.SDKError('selected SDK lacks ZIP source extraction API 1')
        self.archive_metadata = archive_metadata
        return args

    def owner_digest(self):
        files = (Path(__file__).resolve(), Path(sys.modules['network_archive'].__file__).resolve(),
                 Path(sys.modules['tar_archive'].__file__).resolve(),
                 Path(self.archive_metadata.__file__).resolve())
        return hashlib.sha256(b''.join(hashlib.sha256(path.read_bytes()).digest() for path in files)).hexdigest()

    def recipe(self, exported):
        root = Path(exported)/self.PACKAGE
        common = self.read(root/'Makefile.common')
        makefile = self.read(root/'Makefile')
        dist = re.findall(rb'^SQLITE3_DISTVERSION=\s*([0-9]{7})\s*$', common, re.M)
        version = re.findall(rb'^SQLITE3_VERSION=\s*([0-9]+)\.([0-9]+)\.([0-9]+)\s*$', common, re.M)
        self.require(len(dist) == len(version) == 1, 'ambiguous SQLite source family version')
        major, minor, patch = map(int, version[0])
        self.require(int(dist[0]) == major*1000000 + minor*10000 + patch*100,
                     'SQLite source archive and package versions differ')
        self.require(re.search(rb'^DISTNAME=\s*sqlite-autoconf-\$\{SQLITE3_DISTVERSION\}\s*$', makefile, re.M),
                     'unexpected SQLite core source selection')
        name = 'sqlite-src-' + dist[0].decode('ascii')
        metadata, patches = self.archive_metadata.read_recipe(root, name+'.zip', name)
        metadata['recipe']['Makefile.common'] = hashlib.sha256(common).hexdigest()
        return metadata, patches


if __name__ == '__main__':
    Owner().main()
