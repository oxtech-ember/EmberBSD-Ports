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
    def test_selected_git_works_outside_isolated_host_path(self):
        git = shutil.which('git')
        self.assertIsNotNone(git)
        git = os.path.realpath(git)
        repo = self.root / 'os-git'
        repo.mkdir()
        subprocess.run([git, 'init', '-q', str(repo)], check=True)
        subprocess.run([git, '-C', str(repo), '-c', 'user.name=Fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
        expected = subprocess.check_output([git, '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        options, remaining = pipeline.compile_test_options(['--git', git, '/compiler', '/sysroot', '/output'])
        self.assertEqual(remaining, ['/compiler', '/sysroot', '/output'])
        self.assertEqual(options.git, git)
        self.host_prefix.mkdir(exist_ok=True)
        with patch.dict(os.environ, {'PATH': str(self.host_prefix)}):
            self.assertEqual(pipeline.os_test_source_revision(repo, options.git), expected)

    def test_git_option_rejects_non_absolute_or_nonexecutable(self):
        for value in ('git', '/missing-git', str(self.root)):
            with self.subTest(value=value), self.assertRaises(SDKError):
                pipeline.compile_test_options(['--git', value])

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

    def gcc_sysroot_build_receipt(self):
        target = dict(machine='evbarm', arch='aarch64', triplet='aarch64--netbsd', elf=183)
        compiler = dict(version='16.2.0', triplet='aarch64--netbsd', threads='posix',
            binaries={name: {'sha256': 'a' * 64}
                      for name in pipeline.sysroot_transfer.COMPILER_BINARIES})
        return dict(format='emberbsd-sysroot-build', version=1,
            qualification='built-and-inspected',
            workspace=dict(layout_version=2, target='aarch64', triplet='aarch64--netbsd'),
            sources={name: {'commit': 'b' * 40} for name in ('os', 'ports', 'sdk')},
            signature=dict(target=target, compiler_family='gcc', compiler=compiler,
                           runtime={'fixture': 'GCC runtime bundle'}, host='Darwin-arm64'))

    def test_cli_defaults_to_clang_and_keeps_explicit_gcc(self):
        options, remaining = pipeline.compile_test_options(['/compiler', '/sysroot', '/output'])
        self.assertEqual(options.compiler_family, 'clang')
        self.assertEqual(remaining, ['/compiler', '/sysroot', '/output'])
        options, remaining = pipeline.compile_test_options(['--compiler-family', 'gcc', '/compiler', '/sysroot', '/output'])
        self.assertEqual(options.compiler_family, 'gcc')
        self.assertEqual(remaining, ['/compiler', '/sysroot', '/output'])

    def test_os_source_option_is_optional_and_preserves_compiler_selection(self):
        options, remaining = pipeline.compile_test_options(
            ['--os-source', '/os', '--compiler-family', 'gcc', '/compiler', '/sysroot', '/output'])
        self.assertEqual(options.os_source, '/os')
        self.assertEqual(options.compiler_family, 'gcc')
        self.assertEqual(remaining, ['/compiler', '/sysroot', '/output'])
        options, remaining = pipeline.compile_test_options(['/compiler', '/sysroot', '/output'])
        self.assertIsNone(options.os_source)
        self.assertEqual(remaining, ['/compiler', '/sysroot', '/output'])

    def test_floating_fixture_and_inventory_follow_compiler_family(self):
        for family, chosen, excluded in (
                ('clang', 'float-constexpr-clang.cc', 'float-constexpr.cc'),
                ('gcc', 'float-constexpr.cc', 'float-constexpr-clang.cc')):
            with self.subTest(family=family):
                selected = pipeline.float_constexpr_source(CROSS, family)
                self.assertEqual(selected.name, chosen)
                rows = pipeline.target_test_source_inventory(
                    PROFILE, CROSS, Path(sdk_source.load()), compiler_family=family)
                names = [name for name, _ in rows]
                self.assertTrue(any(name.endswith('/' + chosen) for name in names))
                self.assertFalse(any(name.endswith('/' + excluded) for name in names))
        with self.assertRaises(SDKError):
            pipeline.float_constexpr_source(CROSS, 'other')

    def test_os_target_sources_are_included_in_deterministic_source_inventory(self):
        os_source = self.root / 'os'
        test_dir = os_source / 'ember/tests/target-acceptance'
        for name in ('base-loader-smoke.c', 'fork-cas.c', 'libc-aliases.c', 'libm-valid.c', 'setjmp-valid.c'):
            put(test_dir / name, name.encode())
        rows = pipeline.target_test_source_inventory(
            PROFILE, CROSS, Path(sdk_source.load()), os_source=os_source)
        names = [row[0] for row in rows]
        self.assertEqual(names, sorted(set(names)))
        for name in ('os/ember/tests/target-acceptance/base-loader-smoke.c',
                     'os/ember/tests/target-acceptance/fork-cas.c',
                     'os/ember/tests/target-acceptance/libc-aliases.c',
                     'os/ember/tests/target-acceptance/libm-valid.c',
                     'os/ember/tests/target-acceptance/setjmp-valid.c'):
            self.assertIn(name, names)
        before = dict(rows)
        put(test_dir / 'fork-cas.c', b'changed test source')
        after = dict(pipeline.target_test_source_inventory(
            PROFILE, CROSS, Path(sdk_source.load()), os_source=os_source))
        self.assertNotEqual(before['os/ember/tests/target-acceptance/fork-cas.c'],
                            after['os/ember/tests/target-acceptance/fork-cas.c'])

    def test_os_runtime_program_plan_builds_dynamic_and_static_fork_cas(self):
        os_source = self.root / 'os'
        target_dir = os_source / 'ember/tests/target-acceptance'
        for name in ('base-loader-smoke.c', 'fork-cas.c', 'libc-aliases.c', 'libm-valid.c', 'setjmp-valid.c'):
            put(target_dir / name)
        rows = pipeline.os_runtime_programs(os_source, ['clang', '--target=aarch64--netbsd'],
                                            self.root / 'output')
        by_name = {name: argv for name, argv in rows}
        self.assertEqual(set(by_name), {'libc-aliases', 'base-loader-smoke',
                                        'fork-cas', 'fork-cas-static', 'libm-valid', 'setjmp-valid'})
        self.assertIn(str(target_dir / 'fork-cas.c'), [str(arg) for arg in by_name['fork-cas']])
        self.assertIn('-lm', by_name['libm-valid'])
        self.assertIn(str(target_dir / 'setjmp-valid.c'), [str(arg) for arg in by_name['setjmp-valid']])
        self.assertIn('-static', by_name['fork-cas-static'])
        self.assertNotIn('-static', by_name['fork-cas'])

    def test_guest_runner_emits_nonce_bound_marks_after_each_os_and_consumer_check(self):
        out = self.root / 'guest-output'
        out.mkdir()
        put(out / 'target.txt', b'aarch64\n')
        put(out / 'compiler-family.txt', b'clang\n')
        put(out / 'os-tests.txt', b'yes\n')
        names = ('atomic-tls', 'atomic-tls-lto', 'boundary', 'libc-aliases',
                 'base-loader-smoke', 'fork-cas', 'fork-cas-static', 'libm-valid', 'setjmp-valid')
        for name in names:
            output = 'printf "LOADED /usr/pkg/llvm/lib/libc++.so.1.0\\n"\n' if name == 'boundary' else 'exit 0\n'
            put(out / name, ('#!/bin/sh\n' + output).encode()).chmod(0o755)
        put(out / 'check-runtime.sh', b'#!/bin/sh\nexit 0\n').chmod(0o755)
        fakebin = self.root / 'fakebin'
        put(fakebin / 'uname', b'#!/bin/sh\ncase "$1" in -s) echo NetBSD;; -p) echo aarch64;; *) exit 2;; esac\n').chmod(0o755)
        put(fakebin / 'ldd', b'#!/bin/sh\necho "libc.so.12 => /lib/libc.so.12"\n').chmod(0o755)
        env = dict(os.environ, PATH=str(fakebin) + os.pathsep + '/usr/bin:/bin',
                   EMBERBSD_ACCEPTANCE_NONCE='fixture-nonce')
        env.pop('LD_LIBRARY_PATH', None)
        env.pop('LD_PRELOAD', None)
        result = subprocess.run(['/bin/sh', str(CROSS / 'tests/target/run-target.sh'),
            '--target', 'aarch64', str(out)], env=env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        markers = [line.split()[2] for line in result.stdout.splitlines()
                   if line.startswith('EMBERBSD-CHECK ')]
        self.assertEqual(markers, ['target_c11', 'target_cxx20', 'libc_aliases',
                                   'libm_valid', 'setjmp_valid', 'base_loader_smoke', 'fork_cas'])
        self.assertNotIn('cross_c11', markers)
        self.assertNotIn('cross_cxx20', markers)
        for name in ('target_c11', 'target_cxx20', 'libc_aliases',
                     'libm_valid', 'setjmp_valid', 'base_loader_smoke', 'fork_cas'):
            self.assertIn('EMBERBSD-CHECK fixture-nonce ' + name + ' PASS', result.stdout)

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
        receipt_path = self.sysroot / pipeline.sysroot_transfer.RECEIPT
        pipeline.jsonio.write_json(receipt_path, self.gcc_sysroot_build_receipt())
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
        identity = selected['sysroot_identity']
        self.assertEqual(identity['source_record'], 'build-receipt')
        self.assertEqual(identity['source_record_sha256'], pipeline.sha(receipt_path))
        self.assertEqual(identity['runtime_provenance_sha256'],
                         pipeline.sysroot_transfer._hash_json(
                             self.gcc_sysroot_build_receipt()['signature']['runtime']))
        self.assertEqual(identity['sources'], {name: 'b' * 40 for name in ('os', 'ports', 'sdk')})
        self.assertEqual(identity['execution_acceptance'], 'not-run')

    def test_gcc_target_tests_require_sdk_sysroot_provenance(self):
        with self.assertRaisesRegex(SDKError, 'inspected SDK sysroot'):
            pipeline.gcc_sysroot_identity(self.sysroot, 'aarch64')

    def test_gcc_build_receipt_rejects_other_compiler_or_bad_source_pin(self):
        receipt_path = self.sysroot / pipeline.sysroot_transfer.RECEIPT
        for mutation in ('compiler', 'source'):
            receipt = self.gcc_sysroot_build_receipt()
            if mutation == 'compiler':
                receipt['signature']['compiler']['version'] = '15.2.0'
            else:
                receipt['sources']['os']['commit'] = 'not-a-commit'
            if receipt_path.exists():
                receipt_path.unlink()
            pipeline.jsonio.write_json(receipt_path, receipt)
            with self.subTest(mutation=mutation), self.assertRaises(SDKError):
                pipeline.gcc_sysroot_identity(self.sysroot, 'aarch64')

    def test_gcc_import_receipt_binds_manifest_digest_and_compiler_identity(self):
        sources = {name: 'b' * 40 for name in ('os', 'ports', 'sdk')}
        compiler = dict(version='16.2.0', triplet='aarch64--netbsd', threads='posix',
            binaries={name: 'a' * 64 for name in pipeline.sysroot_transfer.COMPILER_BINARIES})
        manifest = dict(format=pipeline.sysroot_transfer.FORMAT, version=1,
            scope='sysroot-transfer', target='aarch64', triplet='aarch64--netbsd',
            provenance=dict(sources=sources, build_host='Darwin-arm64', compiler=compiler,
                runtime_sha256='c' * 64, build_context_sha256='d' * 64,
                build_receipt_sha256='e' * 64),
            qualification='built-and-inspected', relocation='not-assessed',
            execution_acceptance='not-assessed', root_mode=0o755,
            inventory={'etc': {'kind': 'directory', 'mode': 0o755}},
            unpacked_bytes=0, payload=dict(name='payload.tar.gz', format='gzip-ustar-flat-v1',
                size=1, sha256='f' * 64))
        import_path = self.sysroot / pipeline.application_toolchain.IMPORT_RECORD
        digest = pipeline.sysroot_transfer._hash_json(manifest)
        pipeline.jsonio.write_json(import_path, dict(format='emberbsd-sysroot-import', version=1,
            manifest_sha256=digest, manifest=manifest))
        identity = pipeline.gcc_sysroot_identity(self.sysroot, 'aarch64')
        self.assertEqual(identity['source_record'], 'import-record')
        self.assertEqual(identity['source_record_sha256'], pipeline.sha(import_path))
        self.assertEqual(identity['portable_manifest_sha256'], digest)
        self.assertEqual(identity['sources'], sources)

        import_path.unlink()
        bad_receipt = dict(format='emberbsd-sysroot-import', version=1,
                           manifest_sha256='0' * 64, manifest=manifest)
        pipeline.jsonio.write_json(import_path, bad_receipt)
        with self.assertRaisesRegex(SDKError, 'manifest digest changed'):
            pipeline.gcc_sysroot_identity(self.sysroot, 'aarch64')

        manifest['provenance']['compiler']['version'] = '15.2.0'
        bad_digest = pipeline.sysroot_transfer._hash_json(manifest)
        import_path.unlink()
        pipeline.jsonio.write_json(import_path, dict(format='emberbsd-sysroot-import', version=1,
            manifest_sha256=bad_digest, manifest=manifest))
        with self.assertRaisesRegex(SDKError, 'transfer manifest or target mismatch|compiler'):
            pipeline.gcc_sysroot_identity(self.sysroot, 'aarch64')

    def test_bad_family_and_missing_gcc_runtime_refuse(self):
        with self.assertRaisesRegex(SDKError, 'Unsupported target compiler family'):
            pipeline.select_test_toolchain('system', self.compiler_prefix, self.sysroot, 'aarch64')
        pipeline.jsonio.write_json(self.sysroot / pipeline.sysroot_transfer.RECEIPT,
                                   self.gcc_sysroot_build_receipt())
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
