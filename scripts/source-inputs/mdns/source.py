#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare the common patched mDNSResponder source."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
from network_archive import NetworkOwner

engine = NetworkOwner(__file__, 'net/mDNSResponder', 'PKGVER', 'mDNSResponder', '.tar.gz', 'mDNSResponder-')
PACKAGE = engine.PACKAGE
owner_digest = engine.owner_digest
identity_module = engine.identity_module
def git_effective_identity(git):
    return identity_module().git_package_identity(engine.PORTS, PACKAGE, git)

source_identity = engine.source_identity
recipe = engine.recipe
load_sdk = engine.load_sdk
prepare = engine.prepare
verify = engine.verify
main = engine.main

if __name__ == '__main__':
    main()
