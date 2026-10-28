#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check native Mesa command routing without executing compilers."""
import ast
import configparser
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source
_, arguments = sdk_source.load_sdk()
if arguments:
    raise ValueError('Use --sdk-source SDK')
spec = importlib.util.spec_from_file_location('mesa_producer', PORTS / 'scripts/build-mesa-generators.py')
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


class Native:
    bundle_root = '/selected/host-pkg-g16'
    path = bundle_root + '/gcc16/bin:' + bundle_root + '/bin'
    compiler_family = 'gcc'
    compiler = {'version': '16.2.0'}

    def tool(self, role):
        return self.bundle_root + {'cc': '/gcc16/bin/gcc', 'cxx': '/gcc16/bin/g++'}.get(role, '/bin/' + role)

    def command(self, role):
        return (self.tool(role),)


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self.native = Native()

    def test_module_origin_query_is_executable_python(self):
        compile(producer.MODULE_QUERY, "native-module-query", "exec")

    def test_target_and_ambient_searches_do_not_enter_host_build(self):
        poison = {name: '/target-or-ambient' for name in
                  ('PATH', 'CC', 'CXX', 'CPP', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS',
                   'LDFLAGS', 'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH',
                   'LIBRARY_PATH', 'SDKROOT', 'PKG_CONFIG_PATH', 'PKG_CONFIG_LIBDIR',
                   'PKG_CONFIG_SYSROOT_DIR', 'CMAKE_PREFIX_PATH', 'CMAKE_TOOLCHAIN_FILE',
                   'GCC_EXEC_PREFIX', 'COMPILER_PATH', 'PYTHONPATH', 'PYTHONHOME')}
        with mock.patch.dict(os.environ, poison):
            env = producer.native_environment(self.native, '/source/sdk', Path('/work/tmp'))
        self.assertNotIn('/target-or-ambient', env.values())
        self.assertEqual(env['PATH'], self.native.path)
        self.assertEqual(env['CC'], self.native.tool('cc'))
        self.assertEqual(env['CXX'], self.native.tool('cxx'))
        self.assertEqual(env['PKG_CONFIG_LIBDIR'], '/selected/host-pkg-g16/lib/pkgconfig:/selected/host-pkg-g16/share/pkgconfig')
        self.assertEqual(env['CMAKE_PREFIX_PATH'], self.native.bundle_root)

    def test_meson_native_file_selects_compilers_and_interpreters(self):
        config = configparser.ConfigParser(interpolation=None)
        config.read_string(producer.native_file(self.native))
        binaries = {key: ast.literal_eval(value) for key, value in config['binaries'].items()}
        self.assertEqual(binaries['c'], [self.native.tool('cc')])
        self.assertEqual(binaries['cpp'], [self.native.tool('cxx')])
        self.assertEqual(binaries['python3.15'], [self.native.tool('python')])
        self.assertEqual(binaries['llvm-config'], [self.native.tool('llvm-config')])
        self.assertNotIn('objc', binaries)
        for command in binaries.values():
            self.assertTrue(command[0].startswith(self.native.bundle_root + '/'))
        self.assertIn('gcc16/lib', config['built-in options']['cpp_link_args'])
        self.native.compiler_family = 'clang'
        config.read_string(producer.native_file(self.native))
        self.assertNotIn('gcc16/lib', config['built-in options']['cpp_link_args'])
        for flags in config['built-in options'].values():
            self.assertNotIn('libc++', flags)
            self.assertNotIn('/target', flags)

    def test_llvm_rtti_and_required_upstream_checks(self):
        for rtti, enabled in (('YES', 'true'), ('NO', 'false')):
            with self.subTest(rtti=rtti):
                commands = dict(producer.mesa_commands(self.native, Path('/source'), Path('/work'), 2, rtti))
                setup = commands['configure-mesa']
                self.assertIn('-s', setup)  # -E alone ignores PYTHONNOUSERSITE.
                self.assertIn('-Dcpp_rtti=' + enabled, setup)
                for flag in ('-Db_ndebug=false', '-Dbuild-tests=true', '-Dspirv-tools=enabled',
                             '-Dmesa-clc=enabled', '-Dprecomp-compiler=enabled',
                             '-Dshared-llvm=enabled', '--wrap-mode=nodownload'):
                    self.assertIn(flag, setup)
                self.assertEqual(commands['build-mesa'][0], self.native.tool('ninja'))
                self.assertIn('test', commands['test-mesa'])
                self.assertIn('--print-errorlogs', commands['test-mesa'])
                self.assertIn('--no-rebuild', commands['install-mesa'])
        with self.assertRaisesRegex(ValueError, 'has-rtti'):
            producer.mesa_commands(self.native, Path('/source'), Path('/work'), 2, 'UNKNOWN')

    def test_configured_compiler_cannot_silently_change(self):
        # This is real Meson introspection shape, not executable fixture tools.
        with tempfile.TemporaryDirectory(prefix='mesa-producer-test-') as temporary:
            build = Path(temporary)
            directory = build / 'meson-info'; directory.mkdir()
            metadata = directory / 'intro-compilers.json'
            for family, version in (('gcc', '16.2.0'), ('clang', '23.1.4')):
                self.native.compiler_family = family
                self.native.compiler = {'version': version}
                expected = {'host': {language: {'id': family, 'version': version,
                            'exelist': [self.native.tool(role)]}
                            for language, role in (('c', 'cc'), ('cpp', 'cxx'))}}
                metadata.write_text(json.dumps(expected))
                producer.check_compilers(self.native, build)
                for language in ('c', 'cpp'):
                    for change in ({'id': 'clang' if family == 'gcc' else 'gcc'},
                                   {'version': '1.0.0'}, {'exelist': ['/target/bin/cc']},
                                   {'exelist': ['/usr/bin/ccache', self.native.tool('cc')]}):
                        with self.subTest(family=family, language=language, change=change):
                            value = json.loads(json.dumps(expected))
                            value['host'][language].update(change)
                            metadata.write_text(json.dumps(value))
                            with self.assertRaises(ValueError):
                                producer.check_compilers(self.native, build)



if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
