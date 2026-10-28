#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check notice provenance and rejection of substituted vendor files."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'files/install-notices.py'

class Notices(unittest.TestCase):
    def test_sources_and_symlink_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'source'; vendor = root / 'vendor'
            (source / 'LICENSES').mkdir(parents=True); (source / 'rust').mkdir()
            (source / 'LICENSES/MIT.txt').write_text('project license\n')
            (source / 'REUSE.toml').write_text('version = 1\n')
            (source / 'rust/Cargo.lock').write_text('version = 4\n')
            crate = vendor / 'crate-1.0.0'; crate.mkdir(parents=True)
            (crate / 'Cargo.toml').write_text('[package]\nname="crate"\nversion="1.0.0"\nlicense="MIT"\n')
            (crate / 'LICENSE').write_text('crate license\n')
            output = root / 'out'
            cmd = [sys.executable, str(HELPER), '--source', str(source), '--vendor', str(vendor), '--output', str(output)]
            subprocess.run(cmd, check=True)
            licenses = json.loads((output / 'licenses.json').read_text())
            self.assertEqual(licenses[0]['name'], 'crate')
            expected = hashlib.sha256((crate / 'LICENSE').read_bytes()).hexdigest()
            self.assertIn(expected + '  vendor/crate-1.0.0/LICENSE\n', (output / 'NOTICES.sha256').read_text())
            (crate / 'bad').symlink_to(crate / 'LICENSE')
            self.assertNotEqual(subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode, 0)

if __name__ == '__main__':
    unittest.main()
