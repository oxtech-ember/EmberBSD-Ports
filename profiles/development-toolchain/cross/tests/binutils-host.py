#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the common Binutils host route and its BFD make inputs; no build runs."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

PROFILE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
import sdk_source
ARGS = sdk_source.arguments(sys.argv[1:])
for directory in (PROFILE, PROFILE / 'cross'):
    sys.path.insert(0, str(directory))
import binutils_host
import pipeline
from emberbsd_sdk.errors import SDKError
from emberbsd_sdk.host_prefix import HostPrefix


def file(path, content='fixture\n'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def bfd_tree(work, triplet='x86_64--netbsd'):
    for name in ('src/include/elf/common.h', 'src/include/elf/external.h',
                 'src/include/ansidecl.h', 'src/include/symcat.h', 'build/bfd/bfd.h',
                 'build/bfd/.libs/libbfd.a', 'build/libsframe/.libs/libsframe.a',
                 'build/libiberty/libiberty.a'):
        file(work / name)
    file(work / 'build/bfd/bfdver.h', '#define BFD_VERSION_STRING "GNU Binutils 2.47"\n')
    file(work / 'build/bfd/Makefile', 'srcdir = ' + str(work / 'src/bfd') + '\ntarget_alias = ' + triplet + '\n')
    file(work / 'build/bfd/libbfd.la', "old_library='libbfd.a'\ninstalled=no\n"
         "dependency_libs='../libsframe/libsframe.la -lz -lzstd -ldl'\n")
    file(work / 'build/libsframe/libsframe.la',
         "old_library='libsframe.a'\ninstalled=no\ndependency_libs=''\n")


class BinutilsHostTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='binutils-host-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.work = self.root / 'work'
        prefix = self.root / 'native'
        file(prefix / 'include/zlib.h')
        file(prefix / 'lib/libz.a')
        self.tools = {role: str(prefix / 'bin' / role) for role in binutils_host.ROLES}
        self.tools['python'] = sys.executable
        for role in self.tools:
            if role != 'python':
                file(Path(self.tools[role]), '#!/bin/sh\nexit 97\n').chmod(0o755)
        self.selected = HostPrefix(bundle_root=str(prefix), host={}, compiler={},
            tools=self.tools, driver_components={},
            abi_flags={name: () for name in ('cppflags', 'cflags', 'cxxflags', 'ldflags')})
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start(); self.addCleanup(environment.stop)

    def selection(self, family='clang'):
        with patch.object(binutils_host, 'load_host_prefix', return_value=self.selected) as loader:
            result = binutils_host.native_selection(self.selected.bundle_root, family)
        self.assertEqual(loader.call_args.kwargs['compiler_family'], family)
        return result

    def test_native_selection_keeps_family_tools_flags_and_prefix_path(self):
        for family in ('clang', 'gcc'):
            selected, env = self.selection(family)
            self.assertIs(selected, self.selected)
            self.assertEqual(env['PATH'], selected.path)
            self.assertEqual(env['CC'], self.tools['cc'])
            self.assertEqual(env['CONFIG_SHELL'], self.tools['sh'])
            self.assertEqual(env['CPPFLAGS'], '-I' + selected.bundle_root + '/include')
            self.assertEqual(env['LDFLAGS'], '-L' + selected.bundle_root + '/lib')
            self.assertEqual(env['PKG_CONFIG_PATH'], '')
            self.assertEqual(env['MAKEINFO'], self.tools['true'])

    def test_nested_commands_use_selected_spellings_without_changing_prefix(self):
        self.work.mkdir()
        self.tools['awk'] = self.tools.pop('awk') + '-selected'
        file(Path(self.tools['awk']), '#!/bin/sh\nexit 97\n').chmod(0o755)
        selected, original = self.selection()
        env = binutils_host.native_environment(selected, original, self.work)
        routing = self.work / 'native-tools'
        for command, role in (('awk', 'awk'), ('make', 'gmake'),
                              ('tar', 'bsdtar'), ('c++', 'cxx')):
            self.assertEqual(os.readlink(routing / command), self.tools[role])
        self.assertEqual(env['PATH'], str(routing) + os.pathsep + selected.path)
        self.assertEqual(original['PATH'], selected.path)
        self.assertEqual(env['AWK'], self.tools['awk'])
        self.assertFalse((Path(selected.bundle_root) / 'bin/make').exists())

    def test_conflicting_alias_or_python_is_not_a_fallback(self):
        with patch.dict(os.environ, {'HOST_CC': '/outside/clang'}):
            self.assertRaisesRegex(SDKError, 'HOST_CC differs', self.selection)
        self.tools['python'] = '/outside/python'
        self.assertRaisesRegex(SDKError, 'interpreter differs', self.selection)

    def test_native_zlib_cannot_be_missing_or_an_external_symlink(self):
        library = Path(self.selected.bundle_root) / 'lib/libz.a'
        library.unlink()
        self.assertRaisesRegex(SDKError, 'common native zlib', self.selection)
        library.symlink_to(file(self.root / 'outside/libz.a'))
        self.assertRaisesRegex(SDKError, 'common native zlib', self.selection)

    def test_cli_selects_native_prefix_and_preserves_enclosing_gcc_route(self):
        with patch.object(binutils_host, 'native_selection', return_value='native') as select, \
                patch.object(pipeline, '_build_binutils') as build:
            pipeline.binutils_main(['--target', 'amd64', '--host-prefix', '/native', str(self.work)])
            select.assert_called_once_with('/native', 'clang')
            build.assert_called_with('amd64', str(self.work), None, native='native')
            select.reset_mock()
            pipeline.binutils_main(['--target', 'earmv7hf', str(self.work)], make_override='/gcc/nbgmake')
            select.assert_not_called()
            build.assert_called_with('earmv7hf', str(self.work), '/gcc/nbgmake', native=None)
        self.assertRaisesRegex(SDKError, 'Duplicate', pipeline.binutils_main,
            ['--host-prefix', '/one', '--host-prefix', '/two', str(self.work)])

    def emit(self, triplet='x86_64--netbsd', vector=None):
        def capture(argv, env):
            self.assertEqual(argv, [self.work / 'prefix/bin' / (triplet + '-objdump'), '-i'])
            return vector or binutils_host.VECTORS[triplet] + '\n'
        binutils_host.write_bfd_input(self.work, triplet, capture, {},
                                      host_prefix=self.selected.bundle_root)
        return (self.work / 'host-bfd.mk').read_text()

    def test_actual_libtool_static_dependencies_and_target_vector(self):
        for triplet in binutils_host.VECTORS:
            bfd_tree(self.work, triplet)
            output = self.emit(triplet)
            self.assertIn('EMBER_HOST_BFD_TRIPLET= ' + triplet, output)
            self.assertIn(str(self.work / 'build/bfd/.libs/libbfd.a'), output)
            self.assertIn(str(self.work / 'build/libsframe/.libs/libsframe.a'), output)
            self.assertIn('-lz -lzstd -ldl', output)
            self.assertIn('-Wl,-rpath,' + self.selected.bundle_root + '/lib', output)
            self.assertIn(str(self.work / 'build/libiberty/libiberty.a'), output)
            self.assertNotIn('.la ', output)

    def test_nested_installed_libtool_dependency_is_kept(self):
        bfd_tree(self.work)
        library = file(self.root / 'native/lib/libz.a')
        descriptor = file(library.with_suffix('.la'), "old_library='libz.a'\ninstalled=yes\ndependency_libs='-lpthread'\n")
        source = self.work / 'build/bfd/libbfd.la'
        source.write_text(source.read_text().replace('-lz ', str(descriptor) + ' '))
        output = self.emit()
        self.assertIn(str(library) + ' -lpthread -lzstd -ldl', output)

    def test_optional_sframe_and_platform_link_arguments_follow_metadata(self):
        bfd_tree(self.work, 'armv7--netbsdelf-eabihf')
        source = self.work / 'build/bfd/libbfd.la'
        source.write_text(source.read_text().replace('../libsframe/libsframe.la ', '')
            .replace('-ldl', '-L../libiberty -R/native/lib -R /other/lib -framework CoreFoundation -weak_framework Security'))
        (self.work / 'build/libsframe/.libs/libsframe.a').unlink()
        output = self.emit('armv7--netbsdelf-eabihf')
        self.assertNotIn('libsframe.a', output)
        self.assertIn('-L' + str(self.work / 'build/libiberty'), output)
        self.assertIn('-R/native/lib -R /other/lib -framework CoreFoundation -weak_framework Security', output)
        for malformed in ('-framework', '-R relative', '-framework -lbad'):
            source.write_text("old_library='libbfd.a'\ninstalled=no\ndependency_libs='" + malformed + "'\n")
            self.assertRaises(SDKError, self.emit, 'armv7--netbsdelf-eabihf')

    def test_missing_mixed_or_wrong_target_inputs_refuse_before_output(self):
        for mutation, message in (
                (lambda: (self.work / 'build/libiberty/libiberty.a').unlink(), 'Missing common BFD'),
                (lambda: file(self.work / 'build/bfd/Makefile', 'srcdir = /wrong\ntarget_alias = x86_64--netbsd\n'), 'differs'),
                (lambda: file(self.work / 'build/bfd/bfdver.h', 'BFD 2.42\n'), 'not Binutils 2.47')):
            bfd_tree(self.work)
            mutation()
            self.assertRaisesRegex(SDKError, message, self.emit)
            self.assertFalse((self.work / 'host-bfd.mk').exists())
        bfd_tree(self.work)
        self.assertRaisesRegex(SDKError, 'lacks target vector', self.emit, vector='elf64-littleaarch64\n')
        self.assertFalse((self.work / 'host-bfd.mk').exists())

    def test_libtool_content_cannot_execute_or_inject_make(self):
        for dependency in ('$(touch /bad)', '-lz;false', '../bfd/libbfd.la'):
            bfd_tree(self.work)
            source = self.work / 'build/libsframe/libsframe.la'
            source.write_text(source.read_text().replace("dependency_libs=''", "dependency_libs='" + dependency + "'"))
            self.assertRaises(SDKError, self.emit)
            self.assertFalse((self.work / 'host-bfd.mk').exists())

    def test_real_producer_uses_selected_commands_and_exports_bfd(self):
        ports = self.root / 'ports'
        archive = file(self.root / 'binutils-2.47.tar.xz', 'verified fixture archive')
        data = archive.read_bytes()
        recipe = ports / 'pkgsrc/devel/binutils'
        file(recipe / 'distinfo', 'SHA512 (binutils-2.47.tar.xz) = ' + hashlib.sha512(data).hexdigest() + '\n'
             + 'Size (binutils-2.47.tar.xz) = ' + str(len(data)) + '\n')
        file(recipe / 'patches/patch-fixture')
        file(ports / 'profiles/common-build-tools/sources.tsv', 'binutils-2.47.tar.xz\t'
             + hashlib.sha256(data).hexdigest() + '\thttps://invalid.example/source\n')
        selected, env = self.selection()
        calls = []
        native_mode = True
        def logged(argv, log, environment=None, cwd=None):
            calls.append(([str(word) for word in argv], environment))
            file(log)
            if str(argv[0]) == self.tools['gmake'] and argv[-1] == 'install':
                if native_mode:
                    bfd_tree(self.work)
                for name in pipeline.BINUTILS:
                    file(self.work / 'prefix/bin' / ('x86_64--netbsd-' + name)).chmod(0o755)
                file(self.work / 'prefix/x86_64--netbsd/lib/ldscripts/elf.x')
        def capture(argv, env):
            return 'elf64-x86-64\n' if argv[-1] == '-i' else 'GNU fixture 2.47\n'
        with patch.dict(os.environ, {'EMBER_BINUTILS_ARCHIVE': str(archive), 'CROSS_JOBS': '2'}), \
                patch.object(pipeline, 'PORTS', ports), patch.object(pipeline, 'audit_patches', return_value=['patch-fixture']), \
                patch.object(pipeline, 'host_compilers', side_effect=AssertionError('legacy compiler selection')), \
                patch.object(pipeline, 'logged', logged), patch.object(pipeline, 'capture', capture), \
                patch.object(pipeline, 'policy_sources', return_value=[]):
            pipeline._build_binutils('amd64', str(self.work), native=(selected, env))
        # NetBSD pax/nbtar does not implement --strip-components. The native
        # producer must request the libarchive frontend explicitly.
        self.assertEqual(calls[0][0][0], str(Path(selected.bundle_root) / 'bin/bsdtar'))
        self.assertEqual(calls[1][0][0], self.tools['patch'])
        self.assertEqual(calls[2][0][:2], [self.tools['sh'], str(self.work / 'src/configure')])
        self.assertTrue(all(row[1]['PATH'].split(os.pathsep)[0] == str(self.work / 'native-tools') for row in calls))
        self.assertEqual(env['PATH'], selected.path)
        self.assertIn('--target=x86_64--netbsd', calls[2][0])
        self.assertIn('--with-system-zlib', calls[2][0])
        self.assertTrue((self.work / 'host-bfd.mk').is_file())
        # The existing enclosing GCC producer never promised BFD developer
        # outputs. Its old output set must still suffice without new checks.
        self.work = self.root / 'legacy'
        native_mode = False
        with patch.dict(os.environ, {'EMBER_BINUTILS_ARCHIVE': str(archive), 'CROSS_JOBS': '2'}), \
                patch.object(pipeline, 'PORTS', ports), patch.object(pipeline, 'audit_patches', return_value=['patch-fixture']), \
                patch.object(pipeline, 'host_compilers', return_value=(self.tools['cc'], self.tools['cxx'])), \
                patch.object(pipeline, 'logged', logged), patch.object(pipeline, 'capture', capture), \
                patch.object(pipeline, 'policy_sources', return_value=[]):
            pipeline._build_binutils('amd64', str(self.work), make_override=self.tools['gmake'])
        self.assertTrue((self.work / 'inputs.txt').is_file())
        self.assertFalse((self.work / 'host-bfd.mk').exists())


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *ARGS])
