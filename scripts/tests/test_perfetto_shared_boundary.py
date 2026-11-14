# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Perfetto CLI replay and refresh through the real shared-export selector."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
from unittest.mock import patch
import unittest
from test_pkgsrc_shared_export import SharedExportTest, identity, load, ROOT, SDK

class PerfettoBoundary(SharedExportTest):
    def test_perfetto_boundary(self):
        export = Path(self.temp.name) / 'export'
        identity.create_shared_export(export, self.root, sys.executable, SDK, str(self.tool))
        tree = export / 'pkgsrc'
        recipe = tree / 'devel/perfetto'
        (recipe / 'patches').mkdir(parents=True)
        (recipe / 'Makefile').write_text('DISTNAME= perfetto-1.2\n')
        archive = Path(self.temp.name) / 'perfetto-1.2.tar.gz'
        payload = b'fixture payload\n'
        with tarfile.open(archive, 'w:gz') as tar:
            info = tarfile.TarInfo('perfetto-1.2/file.txt')
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
        raw = archive.read_bytes()
        (recipe / 'distinfo').write_text('SHA512 (perfetto-1.2.tar.gz) = ' + hashlib.sha512(raw).hexdigest() +
            '\nBLAKE2s (perfetto-1.2.tar.gz) = ' + hashlib.blake2s(raw).hexdigest() +
            '\nSize (perfetto-1.2.tar.gz) = ' + str(len(raw)) + ' bytes\n')
        owner = load(ROOT / 'scripts/source-inputs/perfetto/source.py', 'perfetto_boundary')
        owner.load_sdk(['--sdk-source', str(SDK)])
        current = {'api':3, 'package':owner.PACKAGE, 'effective_package_sha256':'a'*64, 'upstream':'1'*40}
        old = dict(current, effective_package_sha256='b'*64)
        state = {'effective':old}
        owner_identity = {'export':'fixture', 'owner_sha256':'c'*64}
        source = Path(self.temp.name) / 'source'
        def cli(action, *args):
            argv = [str(owner.__file__), '--sdk-source', str(SDK), '--git', sys.executable, action, *map(str,args)]
            stdout = io.TextIOWrapper(io.BytesIO(), encoding='utf-8')
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
                owner.main()
        common = ['--archive',archive,'--patch',self.tool,'--pkgsrc-export',export,'--export-patch',self.tool]
        with patch.object(owner, 'PORTS', self.root), patch.object(owner, 'identity_module', return_value=identity), \
             patch.object(owner, 'source_identity', return_value=owner_identity), \
             patch.object(owner, 'git_effective_identity', side_effect=lambda git: state['effective']), \
             patch.object(owner.process, 'capture', side_effect=AssertionError('unexpected exporter')):
            cli('prepare', *common, '--output', source)
            receipt = source / owner.sourceprep.PREPARED_TREE_RECEIPT
            state['effective'] = current
            path = source/'file.txt'
            payload_before = (path.read_bytes(), path.stat().st_mtime_ns)
            cli('verify-source', '--source',source,*common)
            cli('refresh-source', '--source',source,*common)
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), payload_before)
            self.assertEqual(json.loads(receipt.read_text())['identity']['effective'], current)
            with patch.object(owner, 'prepare', side_effect=AssertionError('unexpected replay')):
                cli('verify-source', '--source',source,*common)
                badtool = Path(self.temp.name)/'other-patch'
                badtool.write_text('different'); badtool.chmod(0o755)
                for change in ('dirty', 'stale', 'wrongpatch'):
                    with self.subTest(change=change):
                        marker = export / identity.SHARED_EXPORT_DIRTY
                        if change == 'dirty': marker.write_text('incomplete')
                        if change == 'stale': self.pins['upstream'] = b'2'*40
                        args = common if change != 'wrongpatch' else [*common[:-1],badtool]
                        with self.assertRaises(SystemExit): cli('verify-source','--source',source,*args)
                        if change == 'dirty': marker.unlink()
                        if change == 'stale': self.pins['upstream'] = b'1'*40
            before = receipt.read_bytes()
            (source/'file.txt').write_text('tampered')
            with self.assertRaises(SystemExit): cli('refresh-source','--source',source,*common)
            self.assertEqual(receipt.read_bytes(), before)

if __name__ == '__main__':
    suite = unittest.TestSuite([PerfettoBoundary('test_perfetto_boundary')])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
