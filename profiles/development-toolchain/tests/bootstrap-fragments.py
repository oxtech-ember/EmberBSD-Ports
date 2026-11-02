#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise exported bootstrap argument and configuration logic without building."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import unittest

class Fragments(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='bootstrap-fragments-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.target = self.root / 'target'
        self.bootstrap = self.root / 'bootstrap'
        self.target_fragment = self.root / 'target fragment'
        self.bootstrap_fragment = self.root / 'bootstrap fragment'
        self.target_fragment.write_text('TARGET_MARKER=yes\n')
        self.bootstrap_fragment.write_text('BOOTSTRAP_MARKER=yes\n')
        source = BOOTSTRAP.read_text()
        opt = source[source.index('get_optarg()\n'):source.index('checkarg_missing()\n')]
        pos = source.index('while [ $# -gt 0 ]; do\n')
        parser = source[pos:source.index('\ncheckarg_sane_absolute_path', pos)]
        start = source.index('echo "" >> ${TARGET_MKCONF}', source.index('echo "WRKOBJDIR=', source.index('# opsys specific fiddling')))
        end = source.index('\n# build and register packages', start)
        self.script = ('die() { echo "$*" >&2; exit 1; }\n' + opt +
                       '\nmk_fragment=\nbootstrap_mk_fragment=\n' + parser + '\n' + source[start:end])

    def run_bootstrap(self, *args):
        return subprocess.run([SHELL, '-c', self.script, 'bootstrap', *map(str, args)],
            env={'PATH': '/usr/bin:/bin', 'TARGET_MKCONF': str(self.target),
                 'BOOTSTRAP_MKCONF': str(self.bootstrap)}, text=True, capture_output=True)

    def test_absent_fragments_keep_existing_behavior(self):
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.target.read_text(), self.bootstrap.read_text())

    def test_fragments_are_independent_with_space_paths_and_both_option_forms(self):
        for options in (('--mk-fragment', self.target_fragment, '--bootstrap-mk-fragment', self.bootstrap_fragment),
                        (f'--mk-fragment={self.target_fragment}', f'--bootstrap-mk-fragment={self.bootstrap_fragment}')):
            with self.subTest(options=options):
                self.target.unlink(missing_ok=True)
                self.bootstrap.unlink(missing_ok=True)
                result = self.run_bootstrap(*options)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('TARGET_MARKER=yes\n', self.target.read_text())
                self.assertNotIn('BOOTSTRAP_MARKER', self.target.read_text())
                self.assertIn('BOOTSTRAP_MARKER=yes\n', self.bootstrap.read_text())
                self.assertNotIn('TARGET_MARKER', self.bootstrap.read_text())

    def test_missing_bootstrap_fragment_fails(self):
        for args in (('--bootstrap-mk-fragment', self.root),
                     ('--bootstrap-mk-fragment', self.root / 'absent'),
                     (f'--bootstrap-mk-fragment={self.root / "absent"}',),
                     ('--bootstrap-mk-fragment=',), ('--bootstrap-mk-fragment',)):
            with self.subTest(args=args):
                self.assertNotEqual(self.run_bootstrap(*args).returncode, 0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bootstrap', required=True, type=Path)
    parser.add_argument('--shell', required=True, type=Path)
    args = parser.parse_args()
    BOOTSTRAP = args.bootstrap.resolve(strict=True)
    SHELL = str(args.shell.resolve(strict=True))
    unittest.main(argv=[__file__])
