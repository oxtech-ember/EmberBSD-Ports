#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; fixture checks for shared Clang/GCC target-test routing.
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

PROFILE = Path(__file__).resolve().parents[2]
CROSS = PROFILE / 'cross'
sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
import sdk_source
ARGS = sdk_source.arguments(sys.argv[1:])
sys.path.insert(0, str(PROFILE))
sys.path.insert(0, str(PROFILE / 'cross'))
import pipeline
from emberbsd_sdk.errors import SDKError


def put(path, data=b'fixture'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class TargetToolchainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='target-toolchain-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sysroot = self.root / 'sysroot'
        put(self.sysroot / 'usr/include/stddef.h')
        self.compiler_prefix = self.root / 'target-compiler'
        self.host_prefix = self.root / 'native'
        runtime_root = self.sysroot / 'usr/pkg/llvm/lib'
        self.artifacts = {}
        for role, filename in (('libcxx', 'libc++.so.1.0'),
                               ('libcxxabi', 'libc++abi.so.1.0'),
                               ('libunwind', 'libunwind.so.1.0')):
            path = put(runtime_root / filename, role.encode())
            self.artifacts[role] = {'shared': path.relative_to(self.sysroot).as_posix()}
        gcc_root = self.sysroot / 'usr/pkg/gcc16'
        put(gcc_root / 'lib/gcc/aarch64--netbsd/16.2.0/crtbegin.o')
        (gcc_root / 'include/c++/aarch64--netbsd').mkdir(parents=True)
        put(gcc_root / 'lib/libstdc++.so.7')
        put(gcc_root / 'lib/libgcc_s.so.1')
        self.native = types.SimpleNamespace(host={'os': 'Darwin', 'cpu': 'arm64'},
            path=str(self.host_prefix / 'bin'), tool=lambda role: sys.executable)
        self.compiler = {'family': 'clang', 'version': '23.1.0', 'triplet': 'aarch64--netbsd',
                         'reported_triplet': 'aarch64-unknown-netbsd',
                         'binaries': {'readelf': {'selected_path': '/native/bin/llvm-readelf', 'sha256': 'a' * 64},
                                      'cc': {'sha256': 'b' * 64}, 'cxx': {'sha256': 'c' * 64},
                                      'ld': {'sha256': 'd' * 64}},
                         'commands': {'cc': ['/target/bin/clang', '--target=aarch64--netbsd']}}
        self.runtime = {'artifacts': self.artifacts}

    def test_cli_defaults_to_clang_and_keeps_explicit_gcc(self):
        options, remaining = pipeline.compile_test_options(['/compiler', '/sysroot', '/output'])
        self.assertEqual(options.compiler_family, 'clang')
        self.assertEqual(remaining, ['/compiler', '/sysroot', '/output'])
        options, remaining = pipeline.compile_test_options(['--compiler-family', 'gcc', '/compiler', '/sysroot', '/output'])
        self.assertEqual(options.compiler_family, 'gcc')
        self.assertEqual(remaining, ['/compiler', '/sysroot', '/output'])

    def test_source_inventory_covers_controller_and_complete_selected_sdk_package(self):
        rows = pipeline.target_test_source_inventory(PROFILE, CROSS, Path(sdk_source.load()))
        names = [row[0] for row in rows]
        self.assertEqual(names, sorted(set(names)))
        for name in ('ports/profiles/development-toolchain/host.py',
                     'ports/profiles/development-toolchain/cross/target_options.py',
                     'sdk/src/emberbsd_sdk/__init__.py',
                     'sdk/src/emberbsd_sdk/native_toolset.py',
                     'sdk/src/emberbsd_sdk/application_toolchain.py'):
            self.assertIn(name, names)

    def test_clang_sysroot_identity_binds_verified_runtime_and_receipt_without_acceptance(self):
        build = self.sysroot / pipeline.sysroot_transfer.RECEIPT
        bundle = {'manifest': self.runtime, 'inventory': {}, 'root_mode': 0o755}
        pipeline.jsonio.write_json(build, {'signature': {'runtime': bundle}})
        identity = pipeline.clang_sysroot_identity(self.sysroot, 'aarch64', self.runtime)
        self.assertEqual(identity['source_record'], 'build-receipt')
        self.assertEqual(identity['source_record_sha256'], pipeline.sha(build))
        self.assertEqual(identity['runtime_manifest_sha256'],
                         pipeline.sysroot_transfer._hash_json(self.runtime))
        self.assertEqual(identity['runtime_bundle_sha256'],
                         pipeline.sysroot_transfer._hash_json(bundle))
        self.assertEqual(identity['execution_acceptance'], 'not-run')
        build.unlink()
        manifest = {'runtime': bundle}
        manifest_sha256 = pipeline.sysroot_transfer._hash_json(manifest)
        imported = self.sysroot / pipeline.application_toolchain.IMPORT_RECORD
        pipeline.jsonio.write_json(imported, {'format': 'emberbsd-sysroot-import', 'version': 1,
            'manifest_sha256': manifest_sha256, 'manifest': manifest})
        imported_identity = pipeline.clang_sysroot_identity(self.sysroot, 'aarch64', self.runtime)
        self.assertEqual(imported_identity['source_record'], 'import-record')
        self.assertEqual(imported_identity['source_record_sha256'], pipeline.sha(imported))
        self.assertEqual(imported_identity['portable_manifest_sha256'], manifest_sha256)
        self.assertEqual(imported_identity['execution_acceptance'], 'not-run')

    def test_source_inventory_covers_controller_and_complete_selected_sdk_package(self):
        rows = pipeline.target_test_source_inventory(PROFILE, CROSS, Path(sdk_source.load()))
        names = [row[0] for row in rows]
        self.assertEqual(names, sorted(set(names)))
        for name in ('ports/profiles/development-toolchain/host.py',
                     'ports/profiles/development-toolchain/cross/target_options.py',
                     'sdk/src/emberbsd_sdk/__init__.py',
                     'sdk/src/emberbsd_sdk/native_toolset.py',
                     'sdk/src/emberbsd_sdk/application_toolchain.py'):
            self.assertIn(name, names)

    def test_clang_sysroot_identity_binds_verified_runtime_and_receipt_without_acceptance(self):
        build = self.sysroot / pipeline.sysroot_transfer.RECEIPT
        bundle = {'manifest': self.runtime, 'inventory': {}, 'root_mode': 0o755}
        pipeline.jsonio.write_json(build, {'signature': {'runtime': bundle}})
        identity = pipeline.clang_sysroot_identity(self.sysroot, 'aarch64', self.runtime)
        self.assertEqual(identity['source_record'], 'build-receipt')
        self.assertEqual(identity['source_record_sha256'], pipeline.sha(build))
        self.assertEqual(identity['runtime_manifest_sha256'],
                         pipeline.sysroot_transfer._hash_json(self.runtime))
        self.assertEqual(identity['runtime_bundle_sha256'],
                         pipeline.sysroot_transfer._hash_json(bundle))
        self.assertEqual(identity['execution_acceptance'], 'not-run')

    def test_clang_uses_sdk_api2_compiler_runtime_and_link_commands(self):
        pipeline.jsonio.write_json(self.sysroot / pipeline.sysroot_transfer.RECEIPT,
            {'signature': {'runtime': {'manifest': self.runtime,
                                       'inventory': {}, 'root_mode': 0o755}}})
        compile_commands = {'cc': ['/sdk/clang', '--target=aarch64--netbsd'],
                            'cxx': ['/sdk/clang++', '--target=aarch64--netbsd', '-nostdinc++']}
        link_commands = {'cc': compile_commands['cc'] + ['--rtlib=compiler-rt'],
                         'cxx': compile_commands['cxx'] + ['-stdlib=libc++', '--unwindlib=libunwind']}
        with patch.object(pipeline.native_toolset, 'load_host_prefix', return_value=self.native) as native, \
             patch.object(pipeline.target_toolchain, 'clang_compiler', return_value=self.compiler) as clang, \
             patch.object(pipeline.application_toolchain, 'load_clang_runtime', return_value=self.runtime) as load, \
             patch.object(pipeline.application_toolchain, 'clang_application_commands',
                          side_effect=[compile_commands, link_commands]) as commands, \
             patch.object(pipeline, 'capture', return_value='clang version 23.1.0\n'):
            selected = pipeline.select_test_toolchain('clang', self.compiler_prefix,
                self.sysroot, 'aarch64', self.host_prefix)
        native.assert_called_once_with(self.host_prefix,
            required_roles={'cc', 'cxx', 'cpp', 'python'}, compiler_family='clang')
        clang.assert_called_once_with(self.compiler_prefix, 'aarch64--netbsd',
            host=self.native.host, env={'PATH': self.native.path})
        load.assert_called_once_with(self.sysroot, target='aarch64')
        self.assertEqual(commands.call_args_list[0].kwargs, {'link': False})
        self.assertEqual(commands.call_args_list[1].kwargs, {'link': True})
        self.assertEqual(selected['cc'], compile_commands['cc'])
        self.assertEqual(selected['cxx_link'], link_commands['cxx'])
        self.assertEqual(selected['family'], 'clang')
        self.assertEqual([(row[0], row[1]) for row in selected['runtime_rows']], [
            ('libcxx', '/usr/pkg/llvm/lib/libc++.so.1.0'),
            ('libcxxabi', '/usr/pkg/llvm/lib/libc++abi.so.1.0'),
            ('libunwind', '/usr/pkg/llvm/lib/libunwind.so.1.0')])
        for role, path, digest in selected['runtime_rows']:
            self.assertEqual(hashlib.sha256((self.sysroot / path.lstrip('/')).read_bytes()).hexdigest(), digest)

    def test_clang_requires_explicit_native_prefix(self):
        with self.assertRaisesRegex(SDKError, '--host-prefix'):
            pipeline.select_test_toolchain('clang', self.compiler_prefix, self.sysroot, 'aarch64')

    def test_explicit_gcc_keeps_gcc16_route(self):
        tools = {'gcc': self.root / 'gcc', 'g++': self.root / 'g++',
                 'readelf': self.root / 'readelf'}
        for path in tools.values():
            put(path)
        version = types.SimpleNamespace(stdout=b'gcc version 16.2.0\n', stderr=b'')
        with patch.object(pipeline, 'check_compilers', return_value=tools) as check, \
             patch.object(pipeline.process, 'capture', return_value=version):
            selected = pipeline.select_test_toolchain('gcc', self.compiler_prefix,
                self.sysroot, 'aarch64')
        check.assert_called_once_with(self.compiler_prefix, 'aarch64')
        self.assertEqual(selected['family'], 'gcc')
        self.assertEqual(selected['cc'][0], str(tools['gcc']))
        self.assertIn('--sysroot=' + str(self.sysroot), selected['cc'])
        self.assertTrue(any('usr/pkg/gcc16/include/c++/aarch64--netbsd' in item
                            for item in selected['cxx']))
        self.assertEqual({row[0] for row in selected['runtime_rows']}, {'libstdc++', 'libgcc_s'})

    def test_bad_family_and_missing_gcc_runtime_refuse(self):
        with self.assertRaisesRegex(SDKError, 'Unsupported target compiler family'):
            pipeline.select_test_toolchain('system', self.compiler_prefix, self.sysroot, 'aarch64')
        (self.sysroot / 'usr/pkg/gcc16/lib/libstdc++.so.7').unlink()
        with patch.object(pipeline, 'check_compilers', return_value={
                'gcc': self.root / 'gcc', 'g++': self.root / 'g++', 'readelf': self.root / 'readelf'}):
            with self.assertRaises(FileNotFoundError):
                pipeline.select_test_toolchain('gcc', self.compiler_prefix, self.sysroot, 'aarch64')

    def test_guest_runtime_checker_accepts_manifest_paths_and_rejects_wrong_hash(self):
        out = self.root / 'target-output'
        out.mkdir()
        runtime_root = self.sysroot / 'usr/pkg/llvm/lib'
        rows, loaded = [], []
        for role, name in (('libcxx', 'libc++.so.1.0'),
                           ('libcxxabi', 'libc++abi.so.1.0'),
                           ('libunwind', 'libunwind.so.1.0')):
            path = put(runtime_root / name, role.encode())
            guest_path = '/usr/pkg/llvm/lib/' + name
            rows.append(f'{role}\t{guest_path}\t{hashlib.sha256(path.read_bytes()).hexdigest()}\n')
            loaded.append('LOADED ' + guest_path + '\n')
        (out / 'compiler-family.txt').write_text('clang\n')
        (out / 'runtime-files.tsv').write_text(''.join(rows))
        (out / 'loaded.txt').write_text(''.join(loaded))
        bin_dir = self.root / 'bin'
        realpath = shutil.which('realpath')
        self.assertIsNotNone(realpath)
        put(bin_dir / 'realpath', ('#!/bin/sh\ncase "$1" in\n'
             '/usr/pkg/llvm/*) printf "%s\\n" "$FAKE_SYSROOT$1";;\n'
             '*) exec ' + realpath + ' "$@";;\nesac\n').encode()).chmod(0o755)
        environment = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'],
                           FAKE_SYSROOT=str(self.sysroot))
        script = CROSS / 'tests/target/check-runtime.sh'
        passed = subprocess.run(['/bin/sh', str(script), str(out)], env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(passed.returncode, 0, passed.stderr.decode())
        (out / 'loaded.txt').write_text(''.join(loaded[1:]))
        missing = subprocess.run(['/bin/sh', str(script), str(out)], env=environment,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn(b'Expected one loaded libcxx', missing.stderr)
        (out / 'loaded.txt').write_text(''.join(loaded))
        rows[0] = rows[0][:-2] + ('0' if rows[0][-2] != '0' else '1') + '\n'
        (out / 'runtime-files.tsv').write_text(''.join(rows))
        failed = subprocess.run(['/bin/sh', str(script), str(out)], env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn(b'SHA256 mismatch', failed.stderr)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *ARGS])
