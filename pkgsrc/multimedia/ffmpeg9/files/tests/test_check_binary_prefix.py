#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import subprocess, sys, tempfile, unittest
from pathlib import Path
SCRIPT = Path(__file__).with_name('check_binary_prefix.py')
class TestPrefix(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); (self.root / 'payload').mkdir()
        (self.root / 'config.h').write_text('#define FFMPEG_CONFIGURATION "--prefix=/producer --enable-gpl"\n')
    def check(self, data, expected):
        (self.root / 'payload' / 'binary').write_bytes(data)
        p = subprocess.run([sys.executable, str(SCRIPT), '--payload', str(self.root / 'payload'), '--config-h', str(self.root / 'config.h'), '--producer-prefix', '/producer'], capture_output=True)
        self.assertEqual(p.returncode, expected, p.stderr.decode())
    def test_exact(self): self.check(b'\0--prefix=/producer --enable-gpl\0', 0)
    def test_other_prefix(self): self.check(b'\0--prefix=/producer --enable-gpl\0/producer/secret\0', 1)
    def test_near_match(self): self.check(b'\0--prefix=/producer --enable-gpl-modified\0', 1)
    def test_prepend_nearmatch(self): self.check(b'\0other--prefix=/producer --enable-gpl\0', 1)
    def test_missing_terminator(self): self.check(b'\0--prefix=/producer --enable-gpl!', 1)
if __name__ == '__main__': unittest.main()
