#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD common builtins regression, extended for the shared runtime owner (AI-assisted).
"""Actual stage validation and failed-producer boundaries with synthetic ELF."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
FILES = Path(__file__).resolve().parents[1] / 'files'

def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

owner = module(FILES / 'source.py', 'stage_source')
arguments = owner.load_sdk(sys.argv[1:])
producer = module(FILES / 'build.py', 'stage_builder')
from emberbsd_sdk import llvm_runtime, targets
from emberbsd_sdk.errors import CommandError, SDKError


def object_archive(machine):
    data = bytearray(64)
    data[:7] = b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HHI', data, 16, 1, machine, 1)
    struct.pack_into('<H', data, 52, 64)
    entry = f'{"builtin.o/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n'.encode()
    return b'!<arch>\n' + entry + bytes(data)


class BuildStage(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='runtime-stage-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.source = self.root / 'source'
        for name in ('LICENSE.TXT', 'CREDITS.TXT', 'lib/builtins/LICENSE.EmberBSD-BINARY128.TXT',
                     'lib/profile/LICENSE.EmberBSD-GCOV.TXT'):
            path = self.source / 'compiler-rt' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Fixture license: ' + name + '\n')
        self.stage, self.work = self.root / 'stage', self.root / 'work'
        self.args = SimpleNamespace(source=str(self.source), stage=str(self.stage), work=str(self.work),
            sysroot=str(self.root / 'base'), os_source='/selected/os', git='/selected/git', target='aarch64',
            phase='builtins', jobs=2, host_prefix='/native', target_prefix='/target', host_compiler_family='clang')
        self.recipe = dict(ports_revision='a'*40, files={'pkgsrc/lang/compiler-rt/files/build.py': 'b'*64})
        self.prepared = dict(llvm_version='23.1.4', source=dict(archive='llvm-project-23.1.4.src.tar.xz', sha512='c'*128),
                             recipe=self.recipe)
        self.context = dict(os_revision='d'*40, files={'usr/include/stdint.h': 'e'*64}, symlinks={})
        self.compiler = dict(version='23.1.4', resource_dir='/target/lib/clang/23', binaries={
            role: dict(selected_path='/target/bin/' + name)
            for role, name in [('cc','clang'), ('cxx','clang++'), ('ld','ld.lld'), ('ar','llvm-ar'),
                               ('ranlib','llvm-ranlib'), ('nm','llvm-nm'), ('strip','llvm-strip')]})
        self.native = SimpleNamespace(tool=lambda role: '/native/bin/' + role, path='/native/bin',
                                      bundle_root='/native', host={'os':'Darwin', 'cpu':'arm64'})
        self.selected = SimpleNamespace(definition=targets.target_definition('aarch64'), base=self.root/'base',
            work=self.work, stage=self.stage, native=self.native, environment={'PATH':'/native/bin'},
            compiler=self.compiler, recipe=self.recipe, context=self.context, bootstrap=None, bootstrap_root=None)

    def run_build(self, *, machine=183, changed_base=False, fail=False, extra=False, changed_compiler=False, empty_archive=False, changed_source=False, source_import=False):
        def runner(owner, command, work, environment, log):
            if source_import:
                (self.source / 'generator_fixture.py').write_text('value = 1\n')
                subprocess.run([sys.executable, '-c', 'import generator_fixture'],
                               cwd=self.source, env=environment, check=True)
            if fail:
                raise CommandError(7, command)
            if command[-1] == 'install-builtins':
                target = self.stage / 'usr/pkg/llvm/lib/clang/23/lib/netbsd/libclang_rt.builtins-aarch64.a'
                target.parent.mkdir(parents=True)
                target.write_bytes(b'!<arch>\n' if empty_archive else object_archive(machine))
                if extra:
                    target.with_name('libunrelated.a').write_bytes(object_archive(machine))
        def binding(native, *, bindings, environment):
            # Real selected commands are checked by native-shell-routing.py.
            # This fixture isolates artifact and failed-producer boundaries.
            self.assertIs(native, self.native)
            self.assertEqual(bindings, str(self.work / 'native-commands'))
            self.assertTrue(self.work.is_dir())
            return dict(environment)
        context = dict(self.context, os_revision='f'*40) if changed_base else self.context
        with patch.object(owner, 'verify_source', side_effect=[self.prepared,
                 dict(self.prepared, tree_sha256='f'*64) if changed_source else self.prepared]), \
             patch.object(producer, 'inspect_inputs', return_value=self.selected), \
             patch.object(producer, 'base_inputs', return_value=context), \
             patch.object(producer, 'effective_recipe', return_value=self.recipe), \
             patch.object(producer, 'execute', side_effect=runner), \
             patch('emberbsd_sdk.native_checks.check_environment', side_effect=binding), \
             patch('emberbsd_sdk.target_toolchain.clang_compiler', return_value={} if changed_compiler else self.compiler):
            return producer.build(owner, self.args)

    def test_riscv_full_runtime_is_refused_before_stage_access(self):
        import emberbsd_sdk
        sdk = str(Path(emberbsd_sdk.__file__).resolve().parents[2])
        common = [sys.executable, '-B', str(FILES / 'runtime.py'), '--sdk-source', sdk]
        commands = [
            ['verify', '--stage', '/missing-rv32-stage', '--target', 'riscv32'],
            ['build', '--source', '/missing', '--sysroot', '/missing', '--os-source', '/missing',
             '--host-prefix', '/missing', '--target-prefix', '/missing', '--work', '/missing-work',
             '--stage', '/missing-stage', '--target', 'riscv32'],
        ]
        for command in commands:
            for extra in ([], ['--phase', 'full']):
                result = subprocess.run(common + command + extra, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('riscv32 supports only builtins and bootstrap', result.stderr)

    def test_installed_builtins_have_actual_inventory_and_no_full_runtime_claim(self):
        result = self.run_build()
        self.assertEqual(result['components'], ['builtins'])
        self.assertIn('LICENSE.TXT', '\n'.join(result['files']))
        self.assertEqual(llvm_runtime.validate_stage(self.stage, target='aarch64'), result)
        with self.assertRaisesRegex(SDKError, 'required runtime components'):
            llvm_runtime.validate_stage(self.stage, required_components=llvm_runtime.FULL_COMPONENTS)

    def test_generators_leave_prepared_sources_unchanged(self):
        self.run_build(source_import=True)
        self.assertFalse(list(self.source.rglob('__pycache__')))

    def test_failed_final_archive_validation_removes_written_manifest(self):
        with self.assertRaises(SDKError):
            self.run_build(empty_archive=True)
        self.assertFalse((self.stage/'runtime.json').exists())

    def test_wrong_target_object_has_no_completed_manifest(self):
        with self.assertRaises(SDKError):
            self.run_build(machine=62)
        self.assertFalse((self.stage/'runtime.json').exists())

    def test_unrelated_installed_library_is_rejected(self):
        with self.assertRaisesRegex(SDKError, 'unexpected file or link'):
            self.run_build(extra=True)
        self.assertFalse((self.stage/'runtime.json').exists())

    def test_changed_base_is_rejected(self):
        with self.assertRaisesRegex(SDKError, 'base headers or libraries changed'):
            self.run_build(changed_base=True)
        self.assertFalse((self.stage/'runtime.json').exists())

    def test_changed_prepared_source_is_rejected(self):
        with self.assertRaisesRegex(SDKError, 'prepared LLVM source changed'):
            self.run_build(changed_source=True)
        self.assertFalse((self.stage/'runtime.json').exists())

    def test_changed_compiler_is_rejected(self):
        with self.assertRaisesRegex(SDKError, 'target compiler changed'):
            self.run_build(changed_compiler=True)
        self.assertFalse((self.stage/'runtime.json').exists())

    def test_recovery_checks_cached_cmake_inputs_before_mutation(self):
        work = self.root / 'cached-build'
        work.mkdir()
        cache = work / 'CMakeCache.txt'
        command = ['/selected/cmake', '-S', '/selected/source', '-B', str(work),
                   '-D', 'CMAKE_SYSROOT=/target/base', '-D', 'CMAKE_C_COMPILER=/selected/clang']
        lines = ['CMAKE_HOME_DIRECTORY:INTERNAL=/selected/source',
                 'CMAKE_SYSROOT:PATH=/target/base']
        cache.write_text(chr(10).join(lines + ['CMAKE_C_COMPILER:STRING=/foreign/compiler']))
        with self.assertRaisesRegex(SDKError, 'cached CMake input differs'):
            producer.check_cmake_cache(owner, work, command)
        cache.write_text(chr(10).join(lines + ['CMAKE_C_COMPILER:STRING=/selected/clang']))
        producer.check_cmake_cache(owner, work, command)

    def test_recovery_rejects_modified_stage_archive(self):
        source = self.root / 'prepared'
        work = self.root / 'cached'
        stage = self.root / 'stage-check'
        for path in (source / 'libunwind/include', work / 'builtins/lib',
                     work / 'bootstrap/lib', stage / 'usr/pkg/llvm/include',
                     stage / 'usr/pkg/llvm/lib'):
            path.mkdir(parents=True)
        (source / 'libunwind/include/unwind.h').write_bytes(b'header')
        (stage / 'usr/pkg/llvm/include/unwind.h').write_bytes(b'header')
        (work / 'builtins/lib/libclang_rt.builtins-aarch64.a').write_bytes(b'builtins')
        (work / 'bootstrap/lib/libunwind.a').write_bytes(b'unwind')
        builtins = stage / 'usr/pkg/llvm/lib/libclang_rt.builtins-aarch64.a'
        builtins.write_bytes(b'wrong')
        (stage / 'usr/pkg/llvm/lib/libunwind.a').write_bytes(b'unwind')
        (work / 'bootstrap/install_manifest.txt').write_text('/usr/pkg/llvm/include/unwind.h' + chr(10) + '/usr/pkg/llvm/lib/libunwind.a')
        with self.assertRaisesRegex(SDKError, 'stage archive differs'):
            producer.check_bootstrap_artifacts(owner, source, work, stage)
        builtins.write_bytes(b'builtins')
        producer.check_bootstrap_artifacts(owner, source, work, stage)
        foreign = stage / 'usr/other/share/licenses/foreign'
        foreign.parent.mkdir(parents=True)
        foreign.write_bytes(b'unexpected')
        with self.assertRaisesRegex(SDKError, 'unexpected bootstrap stage payload'):
            producer.check_bootstrap_artifacts(owner, source, work, stage)

    def test_recovery_refuses_pending_ninja_without_manifest(self):
        self.args.phase = 'bootstrap'
        self.work.mkdir()
        self.stage.mkdir()
        with patch.object(owner, 'verify_source', return_value=self.prepared), \
             patch.object(producer, 'inspect_inputs', return_value=self.selected), \
             patch.object(producer, 'check_cmake_cache'), \
             patch('emberbsd_sdk.native_checks.check_environment', return_value={}), \
             patch.object(owner.process, 'capture', return_value=SimpleNamespace(stdout=b'[1/1] CC changed.o')), \
             patch.object(producer, 'finalize') as finish:
            with self.assertRaisesRegex(SDKError, 'pending build work'):
                producer.recover_bootstrap(owner, self.args)
            finish.assert_not_called()
        self.assertFalse((self.stage / 'runtime.json').exists())

    def test_failed_command_retains_status_and_no_completed_manifest(self):
        with self.assertRaises(CommandError) as error:
            self.run_build(fail=True)
        self.assertEqual(error.exception.returncode, 7)
        self.assertFalse((self.stage/'runtime.json').exists())


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *arguments], verbosity=2)
