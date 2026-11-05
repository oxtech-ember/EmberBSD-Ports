#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Prepare an explicitly selected shared ML source owner; no version resolver."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS / 'scripts/source-inputs/common'))
from network_archive import NetworkOwner
from tar_archive import prepare, verify, shared_tree

class Owner(NetworkOwner):
    def __init__(self, package):
        super().__init__(__file__, package, '', package.rsplit('/', 1)[1], '', '')

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
        def field(name, pattern):
            values = re.findall(r'^' + name + r'=\s*(' + pattern + r')\s*$', text, re.M)
            self.require(len(values) == 1, 'ambiguous ' + name)
            return values[0]
        dist = field('DISTNAME', r'[A-Za-z0-9_.+-]+')
        suffix = field('EXTRACT_SUFX', r'\.[A-Za-z0-9.]+') if re.search(r'^EXTRACT_SUFX=', text, re.M) else '.tar.gz'
        source = field('WRKSRC', r'\$\{WRKDIR\}/[A-Za-z0-9_.+-]+').split('/', 1)[1]
        return self.archive_metadata.read_recipe(root, dist + suffix, source)

    def prepare(self, archive, output, patch, git, scoped_identity=False, exported=None):
        return prepare(self, archive, output, patch, git, scoped_identity, exported)

    def verify(self, source, git, archive=None, patch=None, pkgsrc_export=None, export_patch=None):
        return verify(self, source, git, archive, patch, pkgsrc_export, export_patch)

    def shared_tree(self, selected):
        return shared_tree(self, selected)

if __name__ == '__main__':
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--package', required=True)
    opts, rest = p.parse_known_args()
    if not re.fullmatch(r'devel/(ruy|pthreadpool|gemmlowp|farmhash|ml-dtypes|neon2sse|fft2d|fxdiv)', opts.package):
        raise SystemExit('unsupported explicit ML source package')
    sys.argv = [sys.argv[0], *rest]
    Owner(opts.package).main()
