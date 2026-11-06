#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare the common patched LevelDB source."""
from pathlib import Path
import hashlib
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
from network_archive import NetworkOwner


class Owner(NetworkOwner):
    def __init__(self):
        super().__init__(__file__, 'databases/leveldb', 'LEVELDB_VERSION', 'leveldb', '.tar.gz', 'leveldb-')

    def load_sdk(self, argv):
        args = super().load_sdk(argv)
        from emberbsd_sdk import archive_metadata
        if archive_metadata.ARCHIVE_METADATA_API != 1:
            raise self.SDKError('SDK archive metadata API 1 required')
        self.archive_metadata = archive_metadata
        return args

    def owner_digest(self):
        files = (Path(__file__).resolve(), Path(sys.modules['network_archive'].__file__).resolve(),
                 Path(sys.modules['tar_archive'].__file__).resolve(), Path(self.archive_metadata.__file__).resolve())
        return hashlib.sha256(b''.join(hashlib.sha256(p.read_bytes()).digest() for p in files)).hexdigest()

    def recipe(self, exported):
        root = Path(exported) / self.PACKAGE
        text = self.read(root / 'Makefile').decode('utf-8')
        values = re.findall(r'^DISTNAME=\s*(leveldb-[0-9]+(?:\.[0-9]+)+)\s*$', text, re.M)
        self.require(len(values) == 1, 'ambiguous LevelDB DISTNAME')
        return self.archive_metadata.read_recipe(root, values[0] + '.tar.gz', values[0])


if __name__ == '__main__':
    Owner().main()
