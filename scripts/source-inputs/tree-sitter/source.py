#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare and verify the common pkgsrc tree-sitter runtime source."""
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
from network_archive import NetworkOwner


class Owner(NetworkOwner):
    def __init__(self):
        super().__init__(__file__, 'textproc/tree-sitter', 'TREE_SITTER_VERSION',
                         'tree-sitter', '.tar.gz', 'tree-sitter-')

    def load_sdk(self, argv):
        args = super().load_sdk(argv)
        from emberbsd_sdk import archive_metadata
        if archive_metadata.ARCHIVE_METADATA_API != 1:
            raise self.SDKError('SDK archive metadata API 1 required')
        self.archive_metadata = archive_metadata
        return args

    def recipe(self, exported):
        root = Path(exported) / self.PACKAGE
        text = self.read(root / 'Makefile').decode('utf-8')
        values = re.findall(r'^DISTNAME=\s*(tree-sitter-[0-9]+(?:\.[0-9]+)+)\s*$', text, re.M)
        self.require(len(values) == 1, 'ambiguous tree-sitter DISTNAME')
        distname = values[0]
        return self.archive_metadata.read_recipe(root, distname + '.tar.gz', distname)


def owner_digest():
    return Owner().owner_digest()


def git_effective_identity(git):
    return Owner().git_effective_identity(git)


if __name__ == '__main__':
    Owner().main()
