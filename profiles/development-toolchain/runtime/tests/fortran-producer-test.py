# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; no compiler, source extractor, package DB or SDK reads.
import argparse
import importlib.util
import os
import re
import subprocess
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--ports-source', required=True, type=Path)
parser.add_argument('--sdk-source', required=True)
parser.add_argument('--configured-libgfortran', type=Path)
parser.add_argument('--gnu-make', type=Path)
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
        # Keep fixtures outside the input source; TMPDIR selects the work volume.
        self.root = Path(tempfile.mkdtemp(prefix='fortran-producer-')).resolve()
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

    def context_fixture(self):
        producer = runtime.FortranRuntime(self.args)
        gcc = self.root / 'generation/build/gcc'
        libgcc = self.root / 'base/build/x86_64--netbsd/libgcc'
        gcc.mkdir(parents=True)
        libgcc.mkdir(parents=True)
        for owner in (self.root / 'generation', self.root / 'base'):
            (owner / 'src/gcc').mkdir(parents=True)
            (owner / 'src/gcc/BASE-VER').write_text('16.2.0\n')
            (owner / 'src/libgcc').mkdir()
            (owner / 'src/libgcc/gthr-posix.h').write_text('fixture thread interface\n')
        (gcc / 'Makefile').write_text('target=x86_64--netbsd\n')
        for name in ('auto-host.h', 'config.h', 'tconfig.h', 'tm.h'):
            (gcc / name).write_text('fixture generated header\n')
        (gcc / 'version.h').write_text('#define version_string "16.2.0"\n')
        (libgcc / 'Makefile').write_text('target_noncanonical = x86_64--netbsd\nthread_header = gthr-posix.h\n')
        (libgcc / 'auto-target.h').write_text('fixture target header\n')
        header = self.root / 'base/src/libgcc/gthr-posix.h'
        header.write_text('fixture thread interface\n')
        (libgcc / 'gthr-default.h').symlink_to(header)
        installed = self.root / 'base/stage/usr/pkg/gcc16/include/c++/x86_64--netbsd/bits'
        installed.mkdir(parents=True)
        (installed / 'gthr-default.h').write_text('different transformed C++ header fixture\n')
        return producer, gcc, libgcc

    def test_context_provider_roles_without_mutation(self):
        producer, gcc, libgcc = self.context_fixture()
        producer.context = producer.inspect_build_context()
        before = producer.context
        self.work.mkdir()
        producer.bind_build_context()
        self.assertEqual((self.work / 'build/gcc').resolve(), gcc)
        self.assertEqual((self.work / 'build/x86_64--netbsd/libgcc').resolve(), libgcc)
        self.assertEqual(producer.inspect_build_context(), before)
        self.assertIn(str(self.work / 'build-context.json'), producer.inputs)

    def test_context_wrong_source_version_and_target(self):
        producer, gcc, libgcc = self.context_fixture()
        for path, changed in ((gcc / 'Makefile', 'target=aarch64--netbsd\n'),
                              (libgcc / 'Makefile', 'target_noncanonical=aarch64--netbsd\n'),
                              (gcc / 'version.h', '#define version_string "15.2.0"\n'),
                              (self.root / 'base/src/gcc/BASE-VER', '15.2.0\n')):
            original = path.read_bytes()
            path.write_text(changed)
            with self.subTest(path=path), self.assertRaises(SDKError): producer.inspect_build_context()
            path.write_bytes(original)
        self.assertFalse(self.work.exists())

    def test_context_corrupt_or_missing_required_header(self):
        producer, gcc, libgcc = self.context_fixture()
        header = gcc / 'tconfig.h'
        header.unlink()
        with self.assertRaisesRegex(SDKError, 'Required generated'): producer.inspect_build_context()
        header.write_text('fixture generated header\n')
        (libgcc / 'gthr-default.h').resolve().write_text('corrupted thread header\n')
        with self.assertRaisesRegex(SDKError, 'matching frontend source'): producer.inspect_build_context()
        self.assertFalse(self.work.exists())

    def test_context_symlink_escape_refuses_before_read(self):
        producer, gcc, libgcc = self.context_fixture()
        outside = self.root / 'outside.h'
        outside.write_text('must not be read')
        header = gcc / 'auto-host.h'
        header.unlink()
        header.symlink_to(outside)
        original = runtime.sha
        def inspect(path):
            self.assertNotEqual(Path(path), outside)
            return original(path)
        with patch.object(runtime, 'sha', side_effect=inspect), \
             self.assertRaisesRegex(SDKError, 'escapes its owner'): producer.inspect_build_context()
        self.assertFalse(self.work.exists())

    def test_context_changed_provider_refuses_before_links(self):
        producer, gcc, libgcc = self.context_fixture()
        producer.context = producer.inspect_build_context()
        (gcc / 'auto-host.h').write_text('changed generated header\n')
        self.work.mkdir()
        with self.assertRaisesRegex(SDKError, 'changed before binding'): producer.bind_build_context()
        self.assertEqual(list(self.work.iterdir()), [])

    def test_context_preexisting_paths_are_not_replaced(self):
        producer, gcc, libgcc = self.context_fixture()
        producer.context = producer.inspect_build_context()
        self.work.mkdir()
        (self.work / 'build/x86_64--netbsd').mkdir(parents=True)
        existing = self.work / 'build/x86_64--netbsd/libgcc'
        existing.write_bytes(b'keep this exact file')
        with self.assertRaisesRegex(SDKError, 'exists or escapes'): producer.bind_build_context()
        self.assertEqual(existing.read_bytes(), b'keep this exact file')
        self.assertFalse((self.work / 'build/gcc').exists())

    def test_context_escaped_parent_and_changed_link_refuse(self):
        producer, gcc, libgcc = self.context_fixture()
        producer.context = producer.inspect_build_context()
        self.work.mkdir()
        outside = self.root / 'outside'
        outside.mkdir()
        (self.work / 'build').symlink_to(outside)
        with self.assertRaisesRegex(SDKError, 'exists or escapes'): producer.bind_build_context()
        self.assertEqual(list(outside.iterdir()), [])
        (self.work / 'build').unlink()
        producer.bind_build_context()
        (self.work / 'build/gcc').unlink()
        (self.work / 'build/gcc').symlink_to(libgcc)
        with self.assertRaisesRegex(SDKError, 'link changed'): producer.verify_build_context()

    @unittest.skipUnless(options.configured_libgfortran and options.gnu_make,
                         'Set configured libgfortran and GNU make for the real flag fragment')
    def test_actual_upstream_include_layout_before_after(self):
        producer, gcc, libgcc = self.context_fixture()
        producer.context = producer.inspect_build_context()
        content = (options.configured_libgfortran / 'Makefile').read_text()
        lines = content.splitlines(keepends=True)
        starts = [n for n, line in enumerate(lines) if line.startswith('AM_CPPFLAGS =')]
        self.assertEqual(len(starts), 1)
        selected, n = [], starts[0]
        while True:
            selected.append(lines[n])
            if not lines[n].rstrip().endswith('\\'): break
            n += 1
        declarations = []
        for name in ('srcdir', 'host_subdir', 'MULTISRCTOP', 'MULTIBUILDTOP', 'LIBQUADINCLUDE'):
            values = re.findall(r'^' + name + r' = (.*)$', content, re.M)
            self.assertEqual(len(values), 1)
            declarations.append(name + ' = ' + values[0] + '\n')
        directory = self.work / 'build/x86_64--netbsd/libgfortran'
        directory.mkdir(parents=True)
        (directory.parent / 'libbacktrace').mkdir()
        rules = directory / 'flags.mk'
        rules.write_text(''.join(declarations + selected) + "print:\n\t@printf '%s\\n' $(AM_CPPFLAGS)\n")
        argv = [str(options.gnu_make), '-s', '-f', str(rules), 'print']
        before = subprocess.run(argv, cwd=directory, capture_output=True, check=True, timeout=10)
        flags = before.stdout.decode().splitlines()
        missing = [flag for flag in flags if flag.startswith('-I') and not (directory / flag[2:]).is_dir()]
        self.assertEqual(missing, ['-I../.././gcc', '-I../libgcc'])
        producer.bind_build_context()
        after = subprocess.run(argv, cwd=directory, capture_output=True, check=True, timeout=10)
        self.assertEqual((before.stdout, before.stderr), (after.stdout, after.stderr))
        self.assertTrue(all((directory / flag[2:]).is_dir() for flag in flags if flag.startswith('-I')))
        print('actual-upstream-layout missing-before=' + repr(missing) + ' missing-after=[] flags-unchanged=yes')

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
