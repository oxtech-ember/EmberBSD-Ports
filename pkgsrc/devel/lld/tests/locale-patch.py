#!/usr/bin/env python3
"""Check the LLD locale patch with a BSD patch implementation."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--patch-tool', required=True)
args = parser.parse_args()
patch = Path(__file__).resolve().parents[1] / 'patches/patch-test_lit.cfg.py'
source = ('# header\n' * 15 + '# name: The name of this test suite.\n'
          'config.name = "lld"\n\n'
          '# TODO: Consolidate the logic for turning on the internal shell by default for all LLVM test suites.\n'
          '# See https://github.com/llvm/llvm-project/issues/106636 for more details.\n#\n')
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / 'test').mkdir()
    target = root / 'test/lit.cfg.py'
    target.write_text(source)
    with patch.open('rb') as stream:
        subprocess.run([args.patch_tool, '-F', '0', '-p0'], cwd=root,
                       stdin=stream, check=True)
    expected = source.replace('config.name = "lld"\n',
                              'config.name = "lld"\n\n'
                              '# Keep diagnostics and timestamps stable across host locale settings.\n'
                              'config.environment["LC_ALL"] = "C"\n', 1)
    if target.read_text() != expected:
        raise SystemExit('locale patch changed unexpected source')
print('PASS: BSD patch applies the LLD locale change in the middle of a file')
