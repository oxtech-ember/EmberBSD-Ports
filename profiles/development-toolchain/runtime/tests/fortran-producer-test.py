# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; no compiler, source extractor, package DB or SDK reads.
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--ports-source', required=True, type=Path)
parser.add_argument('--sdk-source', required=True)
options, rest = parser.parse_known_args()
root = Path(__file__).resolve().parents[4]
profile = options.ports_source / 'profiles/development-toolchain'
sys.path[:0] = [str(profile / 'runtime/recipe/files'), str(profile),
               str(root / 'profiles/development-toolchain/cross'), str(profile / 'cross'), str(root / 'profiles/development-toolchain/bootstrap'),
               str(root / 'pkgsrc/lang/gcc16-fortran-runtime/files')]
import sdk_source
sdk_source.load(options.sdk_source)
from emberbsd_sdk.errors import SDKError, ProcessOwnershipError
from emberbsd_sdk.process import ContextLocks
import fortran_support  # Preload the candidate policy in a partial review tree.
import fortran_runtime as runtime


class Producer(unittest.TestCase):
    def setUp(self):
        parent = root / '.fortran-test-fixtures'
        parent.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='producer-', dir=parent)).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        for name in ('pkgsrc', 'sysroot', 'base', 'host'):
            (self.root / name).mkdir()
        (self.root / 'generation/toolchain').mkdir(parents=True)
        (self.root / 'archive').write_bytes(b'fixture')
        self.work = self.root / 'new-work'
        self.args = ['--target', 'amd64'] + [str(self.root / p) for p in
                       ('pkgsrc', 'archive', 'generation/toolchain', 'sysroot', 'base', 'new-work')]
        self.old_jobs = os.environ.get('CROSS_JOBS')
        os.environ['CROSS_JOBS'] = '12'
        self.addCleanup(self.restore_environment)

    def restore_environment(self):
        if self.old_jobs is None: os.environ.pop('CROSS_JOBS', None)
        else: os.environ['CROSS_JOBS'] = self.old_jobs

    def test_parser_refuses_before_work(self):
        bad = [[], self.args + ['extra'], self.args[:1] + ['riscv64'] + self.args[2:],
               ['--check', '--check'] + self.args]
        for args in bad:
            with self.subTest(args=args), self.assertRaises(SDKError):
                runtime.FortranRuntime(args)
            self.assertFalse(self.work.exists())

    def test_existing_work_refuses(self):
        self.work.mkdir()
        with self.assertRaises(SDKError): runtime.FortranRuntime(self.args)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_check_does_not_create_or_build(self):
        producer = runtime.FortranRuntime(['--check'] + self.args)
        with patch.object(producer, 'preflight') as preflight, patch.object(producer, 'build_owned') as build:
            producer.build()
        preflight.assert_called_once()
        build.assert_not_called()
        self.assertFalse(self.work.exists())

    def test_preflight_failure_creates_no_work(self):
        producer = runtime.FortranRuntime(self.args)
        with patch.object(producer, 'preflight', side_effect=SDKError('changed source')):
            with self.assertRaises(SDKError): producer.build()
        self.assertFalse(self.work.exists())

    def test_typed_failure_marks_owned_work(self):
        producer = runtime.FortranRuntime(self.args)
        failure = ProcessOwnershipError(123, 'injected unproven producer', self.root / 'owned.log')
        with patch.object(producer, 'preflight'), patch.object(producer, 'build_owned', side_effect=failure):
            with self.assertRaises(ProcessOwnershipError) as caught: producer.build()
        self.assertIs(caught.exception, failure)
        self.assertTrue((self.work / '.producer-ownership-unproven.json').is_file())

    def test_ordinary_failure_preserves_without_false_quarantine(self):
        producer = runtime.FortranRuntime(self.args)
        with patch.object(producer, 'preflight'), patch.object(producer, 'build_owned', side_effect=SDKError('make failed')):
            with self.assertRaises(SDKError): producer.build()
        self.assertTrue(self.work.is_dir())
        self.assertFalse((self.work / '.producer-ownership-unproven.json').exists())

    def test_replaced_directory_is_not_marked(self):
        producer = runtime.FortranRuntime(self.args)
        def replace():
            self.work.rename(self.root / 'original-work')
            self.work.mkdir()
            raise ProcessOwnershipError(123, 'injected replacement', None)
        with patch.object(producer, 'preflight'), patch.object(producer, 'build_owned', side_effect=replace):
            with self.assertRaisesRegex(ProcessOwnershipError, 'identity changed'): producer.build()
        self.assertEqual(list(self.work.iterdir()), [])

    def test_locked_typed_boundary_retains_real_leases(self):
        args = ['--lock-root', str(self.root), '--host-prefix', str(self.root / 'host')] + self.args
        held = []
        def hold(error):
            for path in (self.work, self.root / 'sysroot', self.root / 'host'):
                with self.assertRaisesRegex(SDKError, 'busy'):
                    with ContextLocks([str(path)], str(self.root)): pass
                held.append(str(path))
            raise RuntimeError('HOLD inspected; stop the injected control')
        # No preflight, source capture, compiler query or actual producer runs.
        with patch.object(runtime.FortranRuntime, 'build', side_effect=ProcessOwnershipError(123, 'injected', None)), \
             patch.object(runtime, 'ownership_hold', side_effect=hold):
            with self.assertRaisesRegex(RuntimeError, 'HOLD inspected'): runtime.locked_main(args)
        self.assertEqual(len(held), 3)
        # The test surrogate exits HOLD intentionally; production never does.
        with ContextLocks([str(self.work)], str(self.root)): pass
        self.assertFalse(self.work.exists())


if __name__ == '__main__': unittest.main(argv=[sys.argv[0]] + rest, verbosity=2)
