#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise Perfetto replay with a small authenticated-export fixture."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
from unittest.mock import patch

sdk = Path(sys.argv[1]).resolve(strict=True)
sys.path.insert(0, str(sdk / 'src'))
owner = Path(__file__).with_name('source.py')
spec = importlib.util.spec_from_file_location('perfetto_owner_fixture', owner)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.load_sdk(['--sdk-source', str(sdk)])
from emberbsd_sdk.errors import SDKError

with tempfile.TemporaryDirectory(prefix='perfetto-shared-test-') as td:
    root = Path(td)
    export = root / 'export'
    recipe = export / 'pkgsrc/devel/perfetto'
    (recipe / 'patches').mkdir(parents=True)
    (recipe / 'Makefile').write_text('DISTNAME= perfetto-1.2\n')
    archive = root / 'perfetto-1.2.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        data = b'fixture payload\n'
        info = tarfile.TarInfo('perfetto-1.2/file.txt')
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    raw = archive.read_bytes()
    (recipe / 'distinfo').write_text('SHA512 (perfetto-1.2.tar.gz) = ' + hashlib.sha512(raw).hexdigest() +
        '\nBLAKE2s (perfetto-1.2.tar.gz) = ' + hashlib.blake2s(raw).hexdigest() +
        '\nSize (perfetto-1.2.tar.gz) = ' + str(len(raw)) + ' bytes\n')
    effective = {'api': 3, 'package': m.PACKAGE, 'effective_package_sha256': 'a'*64, 'upstream': 'b'*40}
    identity = {'export': 'fixture', 'owner_sha256': 'c'*64}
    class Selector:
        valid = True
        @classmethod
        def shared_export(cls, path, ports, git, sdk_source, tool):
            if not cls.valid or Path(path) != export or tool != '/bin/patch':
                raise ValueError('bad export provenance')
            return export / 'pkgsrc'
        @staticmethod
        def current_git_package(*args):
            return False
    with patch.object(m, 'source_identity', return_value=identity), \
         patch.object(m, 'git_effective_identity', return_value=effective), \
         patch.object(m, 'identity_module', return_value=Selector), \
         patch.object(m.process, 'capture', side_effect=AssertionError('unexpected exporter')):
        source = root / 'source'
        m.prepare(archive, source, '/bin/patch', '/usr/bin/git', exported=export/'pkgsrc')
        def verify():
            return m.verify(source, '/usr/bin/git', str(archive), '/bin/patch', str(export), '/bin/patch')
        verify()
        original = archive.read_bytes()
        archive.write_bytes(original + b'bad')
        try: verify()
        except SDKError as exc: assert 'checksum' in str(exc)
        else: raise AssertionError('corrupt archive accepted')
        archive.write_bytes(original)
        rogue = recipe / 'patches/patch-unlisted'
        rogue.write_text('corrupt patch inventory')
        try: verify()
        except SDKError as exc: assert 'patch inventory' in str(exc)
        else: raise AssertionError('corrupt patch inventory accepted')
        rogue.unlink()
        (source / 'file.txt').write_text('changed')
        try: verify()
        except SDKError: pass
        else: raise AssertionError('corrupt source accepted')
        (source / 'file.txt').write_bytes(data)
        Selector.valid = False
        try: verify()
        except ValueError as exc: assert 'provenance' in str(exc)
        else: raise AssertionError('corrupt export provenance accepted')
print('PASS: Perfetto shared-export replay and corruption rejection')
