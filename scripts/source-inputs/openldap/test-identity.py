#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check owner identity binds the version file without boundary ambiguity."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

owner = Path(__file__).with_name('source.py')
spec = importlib.util.spec_from_file_location('openldap_source', owner)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.SDK_SOURCE = '/unused'
module.identity_module = lambda: SimpleNamespace(identity=lambda *args: {})

def identity(script, version):
    module.owner_bytes = lambda: script
    module.version_bytes = lambda: version
    return module.source_identity('/unused')['owner_sha256']

assert identity(b'a', b'bc') != identity(b'ab', b'c'), 'input boundary not bound'
assert identity(b'a', b'bc') != identity(b'a', b'bd'), 'version not bound'

# The SDK fast selector compares the effective identity and treats owner
# digest changes as provenance only; the version must affect that key too.
base = {'api': 2, 'package': 'databases/openldap',
        'effective_package_sha256': '0' * 64, 'upstream': '1' * 40}
module.identity_module = lambda: SimpleNamespace(git_package_identity=lambda *args: dict(base))
module.version_bytes = lambda: b'2.7.1'
old = module.git_effective_identity('/unused')
module.version_bytes = lambda: b'2.7.2'
new = module.git_effective_identity('/unused')
assert old['effective_package_sha256'] != new['effective_package_sha256'], 'version missing from effective key'
print('openldap owner identity: PASS')
