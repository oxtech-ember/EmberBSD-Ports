#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check shared mimalloc Cargo build-script override generation."""
import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest

path = Path(__file__).resolve().parents[1] / 'files/cargo-overrides.py'
spec = importlib.util.spec_from_file_location('mimalloc_cargo_overrides', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class OverrideTest(unittest.TestCase):
    def test_shared_library_and_missing_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            output = root / 'override.toml'
            with self.assertRaisesRegex(ValueError, 'missing'):
                module.write_override(root, output)
            self.assertFalse(output.exists())
            (root / 'libmimalloc.so.3').touch()
            with self.assertRaisesRegex(ValueError, 'missing'):
                module.write_override(root, output)
            (root / 'libmimalloc.so').symlink_to('libmimalloc.so.3')
            module.write_override(root, output)
            self.assertEqual(tomllib.loads(output.read_text()), {
                'mimalloc_sys2': {'rustc-link-lib': ['dylib=mimalloc'],
                                  'rustc-link-search': [str(root)]}})
    def test_reject_relative_directory(self):
        with self.assertRaises(ValueError):
            module.write_override(Path('relative'), Path('unused'))

if __name__ == '__main__':
    unittest.main()
