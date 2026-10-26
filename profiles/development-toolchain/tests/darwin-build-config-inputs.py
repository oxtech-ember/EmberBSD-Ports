#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Source and nonexecuting admission fixtures.
"""Check Darwin build-config input refusal without compiler children."""
import importlib.util
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PROFILE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
import sdk_source
arguments = sdk_source.arguments(sys.argv[1:])
from emberbsd_sdk.errors import SDKError
from emberbsd_sdk import native_toolset
spec = importlib.util.spec_from_file_location('darwin_build_config', Path(__file__).with_name('darwin-build-config.py'))
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class Inputs(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='darwin-config-inputs-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        roles = getattr(subject, 'REQUIRED_ROLES', ('cc',))
        self.tools = {}
        for role in roles:
            path = self.bin / role
            path.write_text('Nonexecuted selected tool fixture\n')
            path.chmod(0o755)
            self.tools[role] = str(path)
        self.flags = dict(cppflags=('-isysroot', str(self.root / 'abi')),
                          cflags=('-O2',), cxxflags=('-O2',), ldflags=('-L' + str(self.root / 'abi/lib'),))
        self.selection = types.SimpleNamespace(tools=self.tools, abi_flags=self.flags,
            host={'os': 'Darwin', 'cpu': 'arm64'},
            compiler={'family': 'gcc', 'version': '16.2.0', 'triplet': 'aarch64-apple-darwin25'},
            bundle_root=str(self.root), tool=lambda role: self.tools[role])
        self.args = types.SimpleNamespace(descriptor=str(self.root / 'descriptor.json'),
            descriptor_sha256='a' * 64, producer_receipt=str(self.root / 'receipt.json'),
            producer_receipt_sha256='b' * 64, tools_bin=self.bin, work=self.root / 'work',
            gcc_source=self.root / 'gcc', math_prefix=self.root / 'math')

    def selected(self):
        with patch.object(native_toolset, 'load_native_toolset', return_value=self.selection) as loader, \
             patch.object(subject.sys, 'executable', self.tools.get('python', sys.executable)), \
             patch.object(subject.subprocess, 'run') as child:
            result = subject.selected_inputs(self.args)
        child.assert_not_called()
        return result, loader

    def test_selection_binds_roles_abi_and_no_ambient_environment(self):
        with patch.dict(os.environ, {'PATH': '/usr/bin:/bin', 'CC': 'clang',
                    'CFLAGS': '--sysroot=/target', 'CONFIG_SITE': '/ambient'}, clear=True):
            (selected, env), loader = self.selected()
        self.assertIs(selected, self.selection)
        self.assertEqual(env['PATH'], str(self.bin))
        self.assertEqual(env['CC'], self.tools['cc'])
        self.assertEqual(env['CXX'], self.tools['cxx'])
        self.assertEqual(env['CPP'], self.tools['cpp'])
        self.assertIn(str(self.root / 'abi'), env['CPPFLAGS'])
        self.assertEqual(env['CFLAGS'], '-O2')
        self.assertEqual(env['CONFIG_SITE'], '/dev/null')
        self.assertEqual(env['GCC_CONFIGURE_SDK'], 'yes')
        self.assertEqual(env['GCC_CONFIGURE_UNAME'], self.tools['uname'])
        self.assertEqual(env['EGREP'], self.tools['grep'] + ' -E')
        self.assertEqual(env['FGREP'], self.tools['grep'] + ' -F')
        self.assertEqual(env['CONFIG_SHELL'], self.tools['sh'])
        self.assertEqual(set(loader.call_args.kwargs['required_roles']), set(subject.REQUIRED_ROLES))

    def test_missing_selectors_refuse_before_admission_or_children(self):
        for name in ('descriptor', 'descriptor_sha256', 'producer_receipt', 'producer_receipt_sha256'):
            original = getattr(self.args, name)
            setattr(self.args, name, None)
            with patch.object(native_toolset, 'load_native_toolset') as loader, \
                 patch.object(subject.subprocess, 'run') as child, self.assertRaises(SDKError):
                subject.selected_inputs(self.args)
            loader.assert_not_called()
            child.assert_not_called()
            setattr(self.args, name, original)

    def test_missing_outside_and_wrong_name_roles_refuse(self):
        for change in ('missing', 'outside', 'alias'):
            original = self.tools['sed']
            if change == 'missing':
                del self.tools['sed']
            elif change == 'outside':
                self.tools['sed'] = '/usr/bin/sed'
            else:
                self.tools['sed'] = str(self.bin / 'gsed')
            with self.assertRaises(SDKError):
                self.selected()
            self.tools['sed'] = original

    def test_missing_printf_and_unknown_path_alias_refuse_before_children(self):
        original = self.tools.pop('printf', None)
        with self.assertRaises(SDKError):
            self.selected()
        if original is not None:
            self.tools['printf'] = original
        outside = self.bin / 'outside-alias'
        outside.symlink_to('/usr/bin/true')
        with self.assertRaises(SDKError):
            self.selected()
        outside.unlink()
        (self.bin / 'unrecorded-tool').write_text('Not an admitted role\n')
        with self.assertRaises(SDKError):
            self.selected()

    def test_external_python_and_wrong_host_refuse(self):
        with patch.object(native_toolset, 'load_native_toolset', return_value=self.selection), \
             patch.object(subject.subprocess, 'run') as child, self.assertRaises(SDKError):
            subject.selected_inputs(self.args)
        child.assert_not_called()
        self.selection.host = {'os': 'Linux', 'cpu': 'aarch64'}
        with self.assertRaises(SDKError):
            self.selected()

    def test_actual_loader_rejects_missing_and_corrupt_descriptor(self):
        with patch.object(subject.subprocess, 'run') as child:
            with self.assertRaises(SDKError):
                subject.selected_inputs(self.args)
            Path(self.args.descriptor).write_text('{}')
            with self.assertRaises(SDKError):
                subject.selected_inputs(self.args)
        child.assert_not_called()
        self.assertFalse(self.args.work.exists())

    def test_compile_and_configure_use_selected_tuple_and_preserve_cause(self):
        self.assertEqual(subject.recipe_build_config(), ['--without-build-config'])
        (selected, env), _ = self.selected()
        self.args.work.mkdir()
        with patch.object(subject, 'run', return_value=types.SimpleNamespace(returncode=0, stdout='')) as run:
            subject.configure(self.args, selected, env, self.args.work / 'configure', [])
        argv = run.call_args.args[0]
        self.assertEqual(argv[0], self.tools['sh'])
        self.assertIn('--build=' + selected.compiler['triplet'], argv)
        self.assertIn('--host=' + selected.compiler['triplet'], argv)
        def child(command, cwd, environment, check=True):
            if '-c' in command:
                (cwd / command[-1]).write_bytes(b'\xcf\xfa\xed\xfe')
            elif '--dump-section' in command:
                Path(command[2].split('=', 1)[1]).write_bytes(b'same frame bytes')
            return types.SimpleNamespace(returncode=1 if '-p' in command else 0, stdout='')
        with patch.object(subject, 'run', side_effect=child) as run, \
             patch.object(subject, 'sections', side_effect=[{'__eh_frame': 16}, {'__eh_frame': 32}]):
            observed = subject.mach_o_probe(self.args, selected, env, self.args.work)
        expected = [self.tools['cc'], *self.flags['cppflags'], *self.flags['cflags']]
        self.assertEqual(run.call_args_list[0].args[0], expected + ['-c', 'conftest.c', '-o', 'conftest.o.g0'])
        self.assertEqual(run.call_args_list[1].args[0], expected + ['-g', '-c', 'conftest.c', '-o', 'conftest.o.g'])
        self.assertEqual(run.call_args_list[2].args[0][0], self.tools['sh'])
        for name in ('strip', 'objdump', 'objcopy'):
            self.assertEqual(observed['GCC_COMPARE_DEBUG_' + name.upper()], self.tools[name])

    def test_legacy_absolute_diagnostics_refuse_before_probe_or_output(self):
        self.args.gcc_source.mkdir()
        configure = self.args.gcc_source / 'configure'
        paths = ('/usr/bin/uname', '/bin/uname', '/bin/arch', '/usr/bin/arch',
                 '/usr/convex/getsysinfo', '/usr/bin/hostinfo', '/bin/machine',
                 '/usr/bin/oslevel', '/bin/universe')
        helper = self.args.gcc_source / subject.DIAGNOSTIC_HELPER
        helper.parent.mkdir()
        helper.write_text(subject.DIAGNOSTIC_SOURCE)
        argv = ['--gcc-source', str(self.args.gcc_source), '--tools-bin', str(self.bin),
                '--math-prefix', str(self.args.math_prefix), '--work', str(self.args.work),
                '--descriptor', self.args.descriptor, '--descriptor-sha256', self.args.descriptor_sha256,
                '--producer-receipt', self.args.producer_receipt,
                '--producer-receipt-sha256', self.args.producer_receipt_sha256]
        for path in paths:
            configure.write_text('emberbsd_host_diagnostic ()\nGCC_CONFIGURE_UNAME\ndiagnostic = `(' + path + ' -p) 2>/dev/null || echo unknown`\n')
            with patch.object(subject, 'selected_inputs', return_value=(self.selection, {})), \
                 patch.object(subject, 'CONFIGURE_FILES', ('configure',)), \
                 patch.object(subject, 'mach_o_probe') as probe, \
                 patch.object(subject.subprocess, 'run') as child, self.assertRaisesRegex(SDKError, 'unselected diagnostic'):
                subject.main(argv)
            child.assert_not_called()
            probe.assert_not_called()
            self.assertFalse(self.args.work.exists())

    def test_wrong_api_and_unqualified_receipt_refuse_before_children(self):
        with patch.object(native_toolset, 'NATIVE_TOOLSET_API', 2), \
             patch.object(native_toolset, 'load_native_toolset') as loader, \
             patch.object(subject.subprocess, 'run') as child, self.assertRaises(SDKError):
            subject.selected_inputs(self.args)
        loader.assert_not_called()
        child.assert_not_called()
        with patch.object(native_toolset, 'load_native_toolset', side_effect=SDKError('Unqualified producer')), \
             patch.object(subject.subprocess, 'run') as child, self.assertRaises(SDKError):
            subject.selected_inputs(self.args)
        child.assert_not_called()

    def test_cli_rejects_missing_selection_and_arbitrary_compiler_words(self):
        argv = ['--gcc-source', str(self.args.gcc_source), '--tools-bin', str(self.bin),
                '--math-prefix', str(self.args.math_prefix), '--work', str(self.args.work)]
        for extra in ([], ['--cc', '/usr/bin/clang -w']):
            with patch.object(subject, 'selected_inputs') as load, \
                 patch.object(subject.subprocess, 'run') as child, \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                subject.main(argv + extra)
            load.assert_not_called()
            child.assert_not_called()
        self.assertFalse(self.args.work.exists())


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *arguments])
