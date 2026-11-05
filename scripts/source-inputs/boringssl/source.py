#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Prepare the common BoringSSL source recipe for explicit consumers."""
import hashlib
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS / 'scripts/source-inputs/common'))
from network_archive import NetworkOwner
from tar_archive import prepare, verify, shared_tree

class Owner(NetworkOwner):
    def __init__(self):
        super().__init__(__file__, 'security/boringssl', '', 'boringssl', '', '')

    def load_sdk(self, argv):
        args = super().load_sdk(argv)
        from emberbsd_sdk import archive_metadata
        if archive_metadata.ARCHIVE_METADATA_API != 1:
            raise self.SDKError('SDK archive metadata API 1 required')
        self.archive_metadata = archive_metadata
        return args

    def owner_digest(self):
        files = [Path(__file__).resolve(), Path(sys.modules['network_archive'].__file__).resolve(),
                 Path(sys.modules['tar_archive'].__file__).resolve(), Path(self.archive_metadata.__file__).resolve()]
        return hashlib.sha256(b''.join(hashlib.sha256(p.read_bytes()).digest() for p in files)).hexdigest()

    def recipe(self, exported):
        root = Path(exported) / self.PACKAGE
        text = self.read(root / 'Makefile').decode('utf-8')
        values = re.findall(r'^DISTNAME=\s*([A-Za-z0-9_.+-]+)\s*$', text, re.M)
        self.require(len(values) == 1, 'ambiguous BoringSSL DISTNAME')
        return self.archive_metadata.read_recipe(root, values[0] + '.tar', values[0])

    def prepare(self, archive, output, patch, git, scoped_identity=False, exported=None):
        return prepare(self, archive, output, patch, git, scoped_identity, exported)

    def verify(self, source, git, archive=None, patch=None, pkgsrc_export=None, export_patch=None):
        return verify(self, source, git, archive, patch, pkgsrc_export, export_patch)

    def shared_tree(self, selected):
        return shared_tree(self, selected)

if __name__ == '__main__':
    Owner().main()
