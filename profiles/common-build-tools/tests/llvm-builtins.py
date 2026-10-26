#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Cross-build dispatch and stage integrity. Synthetic ELF is not target execution."""

import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
from sdk_source import load_sdk
_, arguments = load_sdk()
if arguments:
    raise SystemExit('Use --sdk-source /absolute/EmberBSD-SDK')
spec = importlib.util.spec_from_file_location('builtins_producer', PORTS / 'pkgsrc/lang/llvm/files/build-builtins.py')
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)
from emberbsd_sdk import inventory, llvm_runtime, targets
from emberbsd_sdk.errors import CommandError, SDKError


def object_archive(machine):
    data = bytearray(64)
    data[:7] = b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HHI', data, 16, 1, machine, 1)
    struct.pack_into('<H', data, 52, 64)
    entry = f'{"builtin.o/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n'.encode()
    return b'!<arch>\n' + entry + bytes(data)


class BuiltinsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='llvm-builtins-contract-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.ports = self.root / 'ports'
        self.base = self.root / 'base'
        self.work = self.root / 'work'
        for header in ('sys/param.h', 'stdint.h', 'limits.h'):
            path = self.base / 'usr/include' / header
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('/* actual input fixture */\n')
        self.version = '23.1.4'
        self.archive = self.root / ('llvm-project-' + self.version + '.src.tar.xz')
        with tarfile.open(self.archive, 'w:xz') as packed:
            for name in ('compiler-rt/lib/builtins/CMakeLists.txt', 'compiler-rt/LICENSE.TXT',
                         'cmake/Modules/test.cmake', 'third-party/test.txt', 'libc/test.txt', 'llvm/LICENSE.TXT'):
                data = ('fixture ' + name).encode()
                item = tarfile.TarInfo('llvm-project-' + self.version + '.src/' + name)
                item.size = len(data)
                packed.addfile(item, io.BytesIO(data))
        recipe = self.ports / 'pkgsrc/lang/llvm'
        recipe.mkdir(parents=True)
        (recipe / 'version.mk').write_text('LLVM_VERSION=\t' + self.version + '\n')
        (recipe / 'distinfo').write_text('SHA512 (' + self.archive.name + ') = ' +
                                       hashlib.sha512(self.archive.read_bytes()).hexdigest() + '\n')
        self.source = producer.source_identity(self.ports, self.archive)
        self.target = targets.target_definition('aarch64')
        self.result = dict(format='emberbsd-builtins-build', version=1, target='aarch64',
            target_definition=self.target, work=str(self.work), source=self.source,
            base=dict(os_revision='a' * 40, **producer.header_inputs(self.base)),
            recipe=dict(ports_revision='b' * 40, files={
                'pkgsrc/lang/llvm/version.mk': inventory.sha256_file(recipe / 'version.mk'),
                'pkgsrc/lang/llvm/distinfo': inventory.sha256_file(recipe / 'distinfo')}),
            sources={name: dict(path=str(path), commit=sha * 40, external_gitlinks=[])
                     for name, path, sha in (('ports', self.ports, 'b'), ('os', self.root / 'os', 'a'))},
            inputs=dict(archive=str(self.archive), ports=str(self.ports), base=str(self.base),
                        os=str(self.root / 'os'), git='/usr/bin/git', host_prefix='/native'),
            compiler={'fixture': True}, native={'host': {'os': 'Darwin', 'cpu': 'arm64'}}, environment={'PATH': '/selected/bin'},
            commands=[['cmake', 'configure'], ['cmake', 'build'], ['cmake', 'install']], status='planned')
        self.options = SimpleNamespace(plan=False)

    def run_build(self, *, machine=183, mutate_headers=False, fail=False, extra=False):
        calls = []
        def runner(command, log, **kwargs):
            calls.append(command)
            if fail:
                raise CommandError(7, command)
            if command[-1] == 'install':
                output = self.work / 'stage/usr/pkg/llvm/lib/clang/23/lib/netbsd/libclang_rt.builtins-aarch64.a'
                output.parent.mkdir(parents=True)
                output.write_bytes(object_archive(machine))
                if extra:
                    output.with_name('libunrelated.a').write_bytes(object_archive(machine))
                if mutate_headers:
                    (self.base / 'usr/include/stdint.h').write_text('changed')
        def provenance(path, **kwargs):
            return next(record for record in self.result['sources'].values() if record['path'] == path)
        with patch.object(producer, 'plan', return_value=copy.deepcopy(self.result)), \
             patch('emberbsd_sdk.process.run_logged', side_effect=runner), \
             patch('emberbsd_sdk.provenance.git_source', side_effect=provenance), \
             patch('emberbsd_sdk.target_toolchain.clang_compiler', return_value=self.result['compiler']):
            result = producer.build(self.options)
        return result, calls

    def test_builtin_stage_uses_actual_install_and_has_no_application_runtime_claim(self):
        result, calls = self.run_build()
        self.assertEqual(calls, self.result['commands'])
        self.assertEqual(result['status'], 'built-and-inspected')
        self.assertEqual(result['runtime']['components'], ['builtins'])
        self.assertIn('LICENSE.TXT', '\n'.join(result['runtime']['files']))
        stage = self.work / 'stage'
        llvm_runtime.validate_stage(stage, target='aarch64', ports=self.ports,
                                    ports_revision='b' * 40, base=self.base)
        with self.assertRaisesRegex(SDKError, 'required runtime components'):
            llvm_runtime.validate_stage(stage, required_components=llvm_runtime.FULL_COMPONENTS)

    def test_wrong_target_object_cannot_publish_a_runtime_manifest(self):
        with self.assertRaises(SDKError):
            self.run_build(machine=62)
        self.assertFalse((self.work / 'stage/runtime.json').exists())
        self.assertEqual(json.loads((self.work / 'build.json').read_text())['status'], 'failed')

    def test_unrelated_installed_library_is_rejected(self):
        with self.assertRaisesRegex(SDKError, 'unexpected file or link'):
            self.run_build(extra=True)
        self.assertFalse((self.work / 'stage/runtime.json').exists())

    def test_changed_headers_fail_after_the_producer_and_before_publication(self):
        with self.assertRaisesRegex(SDKError, 'base headers changed'):
            self.run_build(mutate_headers=True)
        self.assertFalse((self.work / 'stage/runtime.json').exists())

    def test_failed_producer_keeps_its_status_and_no_completed_stage(self):
        with self.assertRaises(CommandError) as error:
            self.run_build(fail=True)
        self.assertEqual(error.exception.returncode, 7)
        self.assertFalse((self.work / 'stage/runtime.json').exists())
        self.assertEqual(json.loads((self.work / 'build.json').read_text())['status'], 'failed')

    def test_plan_creates_no_output(self):
        self.options.plan = True
        with patch.object(producer, 'plan', return_value=self.result), \
             patch('emberbsd_sdk.process.run_logged', side_effect=AssertionError('unexpected producer')):
            self.assertEqual(producer.build(self.options), self.result)
        self.assertFalse(self.work.exists())

    def test_bad_source_hash_is_rejected(self):
        self.archive.write_bytes(self.archive.read_bytes() + b'changed')
        with self.assertRaisesRegex(SDKError, 'SHA512 differs'):
            producer.source_identity(self.ports, self.archive)

    def test_source_version_comes_from_common_recipe(self):
        self.assertEqual(self.source['version'], '23.1.4')
        (self.ports / 'pkgsrc/lang/llvm/version.mk').write_text('LLVM_VERSION=23.1.5\n')
        with self.assertRaisesRegex(SDKError, 'archive SHA512'):
            producer.source_identity(self.ports, self.archive)

    def test_base_headers_need_no_existing_application_receipt(self):
        result = producer.header_inputs(self.base)
        self.assertEqual(set(result['files']), {'usr/include/sys/param.h', 'usr/include/stdint.h', 'usr/include/limits.h'})
        self.assertEqual(result['symlinks'], {})

    def test_changed_patch_set_is_not_silently_skipped(self):
        recipe = self.ports / 'pkgsrc/lang/llvm'
        patches = recipe / 'patches'
        patches.mkdir()
        (patches / 'patch-new').write_text('--- cmake/test.cmake.orig\n+++ cmake/test.cmake\n')
        with self.assertRaisesRegex(SDKError, 'patch inventory'):
            producer.source_patches(self.ports)

    def test_new_compiler_rt_recipe_requires_its_full_patch_set(self):
        (self.ports / 'pkgsrc/lang/compiler-rt').mkdir()
        with self.assertRaisesRegex(SDKError, 'connect the common compiler-rt recipe'):
            producer.source_patches(self.ports)

    def test_missing_required_header_is_refused(self):
        (self.base / 'usr/include/stdint.h').unlink()
        with self.assertRaises(SDKError):
            producer.header_inputs(self.base)

    def test_header_link_cannot_select_a_host_header(self):
        path = self.base / 'usr/include/stdint.h'
        path.unlink()
        outside = self.root / 'host-header'
        outside.write_text('foreign')
        path.symlink_to(outside)
        with self.assertRaises(SDKError):
            producer.header_inputs(self.base)

    def test_commands_keep_native_tools_target_and_sysroot_independent(self):
        native = SimpleNamespace(bundle_root='/native', tool=lambda role: '/native/bin/' + role)
        binaries = {role: {'selected_path': '/native/bin/' + name} for role, name in
                    (('cc', 'clang'), ('cxx', 'clang++'), ('ld', 'ld.lld'), ('ar', 'llvm-ar'),
                     ('ranlib', 'llvm-ranlib'), ('nm', 'llvm-nm'), ('strip', 'llvm-strip'))}
        for target in ('aarch64', 'amd64'):
            with self.subTest(target=target):
                definition = targets.target_definition(target)
                commands = producer.commands(self.work, self.base, definition, self.version, native, {'binaries': binaries})
                values = dict(arg[2:].split('=', 1) for arg in commands[0] if arg.startswith('-D'))
                self.assertEqual(values['CMAKE_SYSTEM_NAME'], 'NetBSD')
                self.assertEqual(values['LLVM_DIR'], '/native/lib/cmake/llvm')
                self.assertEqual(values['CMAKE_C_COMPILER_TARGET'], definition['triplet'])
                self.assertEqual(values['CMAKE_SYSROOT'], str(self.base))
                self.assertEqual(values['CMAKE_C_COMPILER'], '/native/bin/clang')
                self.assertEqual(values['CMAKE_ASM_COMPILER'], '/native/bin/clang')
                self.assertEqual(values['CMAKE_POSITION_INDEPENDENT_CODE'], 'ON')
                self.assertEqual(values['COMPILER_RT_BUILTINS_ENABLE_PIC'], 'ON')
                self.assertEqual(values['COMPILER_RT_DEFAULT_TARGET_ONLY'], 'ON')
                self.assertNotIn('COMPILER_RT_DEFAULT_TARGET_TRIPLE', values)
                self.assertEqual(values['COMPILER_RT_INSTALL_PATH:STRING'], 'lib/clang/23')
                self.assertEqual(commands[1][-1], 'builtins')
                self.assertEqual(commands[2][-1], 'install-builtins')
                self.assertNotIn('gcc', ' '.join(commands[0]))


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]], verbosity=2)
