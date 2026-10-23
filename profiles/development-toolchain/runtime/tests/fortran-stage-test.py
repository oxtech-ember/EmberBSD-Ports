# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; synthetic ELF payload controls, no target execution.
import argparse
import importlib.util
import json
from unittest.mock import patch
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

parser = argparse.ArgumentParser()
parser.add_argument('--ports-source', required=True, type=Path)
parser.add_argument('--sdk-source', required=True)
opts, rest = parser.parse_known_args()
base = opts.ports_source / 'profiles/development-toolchain/runtime'
sys.path.insert(0, str(base / 'recipe/files'))
import sdk_source
sdk_source.load(opts.sdk_source)
from emberbsd_sdk.errors import SDKError
saved = sys.argv
sys.argv = ['fixture-import']
spec = importlib.util.spec_from_file_location('base_runtime_fixtures', base / 'tests/package-test.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
sys.argv = saved
candidate = Path(__file__).resolve().parents[4] / 'pkgsrc/lang/gcc16-fortran-runtime/files/fortran_stage.py'
spec = importlib.util.spec_from_file_location('fortran_stage', candidate)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def archive(machine):
    data = fixtures.elf('fixture', machine, kind=1)
    fields = [('probe.o/', 16), ('0', 12), ('0', 6), ('0', 6), ('100644', 8), (str(len(data)), 10)]
    header = ''.join(value.ljust(size) for value, size in fields).encode() + b'`\n'
    return b'!<arch>\n' + header + data + (b'\n' if len(data) % 2 else b'')


class Payload(unittest.TestCase):
    def setUp(self):
        self.directory = Path(__file__).resolve().parents[4] / '.fortran-test-fixtures'
        self.directory.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='stage-', dir=self.directory)).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.configure()

    def configure(self, target='amd64'):
        for child in self.root.iterdir():
            if child.is_dir() and not child.is_symlink(): shutil.rmtree(child)
            else: child.unlink()
        self.target = target
        triplet, machine = {'amd64': ('x86_64--netbsd', 62), 'aarch64': ('aarch64--netbsd', 183)}[target]
        self.lib = self.root / 'usr/pkg/gcc16/lib'
        self.lib.mkdir(parents=True)
        for name in ('libgfortran.so.5', 'libquadmath.so.0'):
            path = self.lib / (name + '.0')
            path.write_bytes(fixtures.elf(name, machine, needed=('libgcc_s.so.1', 'libm.so.0', 'libc.so.12')))
            path.chmod(0o755)
            (self.lib / name).symlink_to(name + '.0')
            family = name.split('.so.')[0]
            (self.lib / (family + '.so')).symlink_to(name)
            (self.lib / (family + '.a')).write_bytes(archive(machine))
        (self.lib / 'libgfortran.spec').write_text('fixture specs\n')
        self.includes = self.lib / 'gcc' / triplet / '16.2.0/include'
        self.includes.mkdir(parents=True)
        for name in ('ISO_Fortran_binding.h', 'quadmath.h', 'quadmath_weak.h'):
            (self.includes / name).write_text('fixture header\n')
        versioned = self.includes.parent
        (versioned / 'finclude').mkdir()
        for name in ('ieee_arithmetic.mod', 'ieee_exceptions.mod', 'ieee_features.mod'):
            (versioned / 'finclude' / name).write_bytes(b'synthetic module fixture')
        (versioned / 'libcaf_single.a').write_bytes(archive(machine))
        (versioned / 'libcaf_single.la').write_text("libdir='/usr/pkg/gcc16/lib/gcc/" + triplet + "/16.2.0'\n")
        (versioned / 'libcaf_single.la').chmod(0o755)

    def inspect(self):
        return stage.inspect_stage(self.root, self.target)

    def test_both_target_roles(self):
        for target in ('amd64', 'aarch64'):
            with self.subTest(target=target):
                self.configure(target)
                value = self.inspect()
                self.assertEqual(len(value['runtime']), 4)
                self.assertEqual(len(value['devel']), 13)
                self.assertFalse(set(value['runtime']) & set(value['devel']))
                self.assertEqual({r['soname'] for r in value['elf'].values()}, {'libgfortran.so.5', 'libquadmath.so.0'})

    def test_wrong_or_mixed_architecture(self):
        for machine in (183, 3):
            with self.subTest(machine=machine):
                path = self.lib / 'libgfortran.so.5.0'
                path.write_bytes(fixtures.elf('libgfortran.so.5', machine))
                with self.assertRaises(SDKError): self.inspect()

    def test_real_dynamic_failures(self):
        cases = [dict(soname='libgfortran.so.4'), dict(relro=False),
                 dict(needed=('libstdc++.so.6',)), dict(rpath='/tmp/private-runtime'), dict(kind=2)]
        for change in cases:
            with self.subTest(change=change):
                self.configure()
                values = dict(soname='libgfortran.so.5')
                values.update(change)
                (self.lib / 'libgfortran.so.5.0').write_bytes(fixtures.elf(**values))
                with self.assertRaises(SDKError): self.inspect()

    def test_missing_runtime_and_devel_data(self):
        for name in ('libquadmath.so.0', 'libgfortran.so', 'libgfortran.a', 'libgfortran.spec'):
            with self.subTest(name=name):
                self.configure()
                (self.lib / name).unlink()
                with self.assertRaises(SDKError): self.inspect()

    def test_unshipped_runtime_alias(self):
        (self.lib / 'libgfortran.so.5').unlink()
        (self.lib / 'libgfortran.so.5').symlink_to('libgfortran.so')
        (self.lib / 'libgfortran.so').unlink()
        (self.lib / 'libgfortran.so').symlink_to('libgfortran.so.5.0')
        with self.assertRaisesRegex(SDKError, 'Unshipped'): self.inspect()

    def test_escaped_aliases(self):
        for target in ('/usr/lib/libgfortran.so.5', '../../../../outside'):
            with self.subTest(target=target):
                self.configure()
                (self.lib / 'libgfortran.so').unlink()
                (self.lib / 'libgfortran.so').symlink_to(target)
                with self.assertRaises(SDKError): self.inspect()

    def test_unknown_or_old_compiler_payload(self):
        for name in ('libgfortran.so.4', 'gfortran', 'libstdc++.so.7'):
            with self.subTest(name=name):
                self.configure()
                (self.lib / name).write_bytes(b'foreign fixture')
                with self.assertRaises(SDKError): self.inspect()

    def test_static_members_and_empty_archive(self):
        for data in (b'!<arch>\n', archive(183), b'not an archive'):
            with self.subTest(size=len(data)):
                self.configure()
                (self.lib / 'libgfortran.a').write_bytes(data)
                with self.assertRaises(SDKError): self.inspect()

    def test_bad_dso_and_sdk_modes(self):
        for name, mode in (('libgfortran.so.5.0', 0o644), ('libgfortran.spec', 0o755)):
            with self.subTest(name=name):
                self.configure()
                (self.lib / name).chmod(mode)
                with self.assertRaises(SDKError): self.inspect()

    def test_libtool_metadata_has_program_install_mode(self):
        metadata = [self.lib / 'libgfortran.la', self.lib / 'libquadmath.la',
                    self.includes.parent / 'libcaf_single.la']
        for path in metadata:
            path.write_text("libdir='/usr/pkg/gcc16/lib'\n")
            path.chmod(0o755)
        self.inspect()
        for path in metadata:
            for mode in (0o644, 0o775, 0o777, 0o4755):
                with self.subTest(path=path.name, mode=oct(mode)):
                    path.chmod(mode)
                    with self.assertRaisesRegex(SDKError, 'Unexpected SDK data mode'): self.inspect()
                    path.chmod(0o755)
        self.inspect()

    def test_literal_libtool_values_and_comments(self):
        path = self.lib / 'libgfortran.la'
        path.write_text("# Files to dlopen/dlpreopen\n"
                        "dependency_libs=' '/usr/pkg/gcc16/lib'/libquadmath.la -lm'\n")
        path.chmod(0o755)
        self.inspect()
        for text in ("dependency_libs=' '/build-host'/work/lib'", "libdir='/usr/pkg/gcc16/'../outside",
                     "libdir='unclosed", "libdir=/usr/pkg/gcc16/lib injected=1",
                     "dependency_libs='$(id)'", "dependency_libs='`id`'", "touch /tmp/leak"):
            with self.subTest(text=text):
                path.write_text(text)
                with self.assertRaises(SDKError): self.inspect()

    def test_libtool_shell_operators_are_not_literal_assignments(self):
        path = self.lib / 'libgfortran.la'
        path.write_text('')
        path.chmod(0o755)
        for suffix in (';id', '&&id', '||id', '|id', '>file', '<file', '&id', '(id)', '\nid'):
            with self.subTest(suffix=suffix):
                path.write_text('libdir=/usr/pkg/gcc16/lib' + suffix)
                with self.assertRaisesRegex(SDKError, 'Invalid Libtool metadata assignment'): self.inspect()
        path.write_text("dependency_libs=' -lm;literal&&value|text>(here)'\n")
        self.inspect()  # Quoted punctuation is literal data. No shell runs.

    def test_foreign_empty_directory(self):
        (self.root / 'usr/pkg/gcc16-foreign').mkdir()
        with self.assertRaises(SDKError): self.inspect()

    def receipt(self):
        work = self.root / 'receipt-work'
        work.mkdir()
        (work / 'stage').mkdir()
        # Move only the fixture target prefix into a separate stage.
        (self.root / 'usr').rename(work / 'stage/usr')
        pkgsrc = self.root / 'pkgsrc'
        (pkgsrc / 'lang/gcc16').mkdir(parents=True)
        (pkgsrc / 'lang/gcc16/Makefile').write_text('synthetic recipe')
        source_archive = self.root / 'gcc-archive'
        source_archive.write_bytes(b'synthetic archive')
        parent_work = self.root / 'parent'
        (parent_work / 'stage').mkdir(parents=True)
        parent = {'metadata': {'PKGNAME': stage.BASE, 'GCC_RUNTIME_TARGET': self.target,
                  'GCC_RUNTIME_SONAMES': 'libgcc_s.so.1,libstdc++.so.7,libatomic.so.3'}, 'files': []}
        tools = {}
        for name in ('gfortran', 'f951', 'nm'):
            path = self.root / name
            path.write_bytes(b'synthetic host tool')
            tools[name] = {'path': str(path), 'sha256': stage.digest(path)}
        cap = {'format': 'emberbsd-gcc16-fortran-capability', 'version': 1,
               'status': 'PASS', 'target': self.target, 'archive_sha256': stage.digest(source_archive),
               'sources': {'recipe': stage.inventory.snapshot_tree(pkgsrc / 'lang/gcc16')},
               'compiler': {'tools': tools, 'version': '16.2.0',
                            'triplet': 'x86_64--netbsd', 'threads': 'posix'}}
        capability = self.root / 'capability.json'
        capability.write_text(json.dumps(cap))
        commands = work / 'commands.json'
        commands.write_text('[]')
        inputs = {str(path): stage.digest(path) for path in (capability, commands)}
        inputs.update({row['path']: row['sha256'] for row in tools.values()})
        value = {'format': 'emberbsd-gcc16-fortran-stage', 'version': 1,
            'status': 'BUILT_AND_INSPECTED', 'target': self.target, 'triplet': 'x86_64--netbsd',
            'source_archive_sha256': stage.digest(source_archive), 'base_runtime_name': stage.BASE,
            'inputs': inputs, 'commands_sha256': stage.digest(commands),
            'compiler_capability': str(capability), 'base_runtime_work': str(parent_work),
            'base_runtime_metadata': parent['metadata'],
            'stage': stage.inspect_stage(work / 'stage', self.target)['stage']}
        receipt = work / 'fortran-stage.json'
        receipt.write_text(json.dumps(value))
        return stage.Stage(work, source_archive, pkgsrc), value, parent, receipt

    def test_receipt_mutations_and_duplicate_claims(self):
        for key, replacement in [('version', True), ('status', 'FAILED'), ('triplet', 'aarch64--netbsd'),
                                 ('base_runtime_name', 'gcc16-runtime-16.2.0nb5')]:
            with self.subTest(key=key):
                self.configure()
                obj, value, parent, receipt = self.receipt()
                with patch.object(stage, 'SOURCE_SHA256', value['source_archive_sha256']), \
                     patch.object(stage.BaseStage, 'verify', return_value=parent):
                    obj.verify()  # The base ABI validator is mocked; the new verifier is real.
                    value[key] = replacement
                    receipt.write_text(json.dumps(value))
                    with self.assertRaises(SDKError): obj.verify()
        self.configure()
        obj, value, parent, receipt = self.receipt()
        receipt.write_text('{' + '"version":1,' + json.dumps(value)[1:])
        with patch.object(stage, 'SOURCE_SHA256', value['source_archive_sha256']), \
             patch.object(stage.BaseStage, 'verify', return_value=parent):
            with self.assertRaisesRegex(SDKError, 'duplicate'): obj.verify()

    def test_changed_tool_input_and_stage_bytes(self):
        for mutation in ('tool', 'command', 'stage', 'quarantine', 'base-overlap'):
            with self.subTest(mutation=mutation):
                self.configure()
                obj, value, parent, receipt = self.receipt()
                with patch.object(stage, 'SOURCE_SHA256', value['source_archive_sha256']), \
                     patch.object(stage.BaseStage, 'verify', return_value=parent):
                    obj.verify()
                    if mutation == 'tool': (self.root / 'f951').write_bytes(b'changed')
                    elif mutation == 'command': (obj.work / 'commands.json').write_text('["changed"]')
                    elif mutation == 'stage': (obj.stage / 'usr/pkg/gcc16/lib/libgfortran.spec').write_text('changed')
                    elif mutation == 'quarantine': (obj.work / '.producer-ownership-unproven.json').write_text('{}')
                    else:
                        old = self.root / 'parent/stage/usr/pkg/gcc16/lib/libgfortran.spec'
                        old.parent.mkdir(parents=True)
                        old.write_text('overlapping real path')
                    with self.assertRaises(SDKError): obj.verify()

    def test_install_refuses_symlink_destination(self):
        obj, value, parent, receipt = self.receipt()
        destination = self.root / 'destination'
        destination.mkdir()
        outside = self.root / 'outside'
        outside.mkdir()
        (destination / 'usr').symlink_to(outside)
        with patch.object(stage, 'SOURCE_SHA256', value['source_archive_sha256']), \
             patch.object(stage.BaseStage, 'verify', return_value=parent):
            with self.assertRaisesRegex(SDKError, 'symlink ancestor'): obj.install('devel', destination)
        self.assertEqual(list(outside.iterdir()), [])

    def test_unversioned_libraries_must_be_real_aliases(self):
        for name in ('libgfortran.so', 'libquadmath.so'):
            for data in (b'regular placeholder', fixtures.elf('libwrong.so.1',62)):
                with self.subTest(name=name, data=data[:16]):
                    self.configure()
                    path = self.lib / name
                    path.unlink()
                    path.write_bytes(data)
                    path.chmod(0o644)
                    with self.assertRaisesRegex(SDKError, 'matching runtime'): self.inspect()

    def test_wrong_development_alias_family(self):
        (self.lib / 'libgfortran.so').unlink()
        (self.lib / 'libgfortran.so').symlink_to('libquadmath.so.0')
        with self.assertRaisesRegex(SDKError, 'matching runtime'): self.inspect()

    def test_host_path_metadata_is_refused(self):
        for text in ('dependency_libs=/build-host/work/lib', 'libdir=/tmp/work/lib', 'dependency_libs=-L/opt/homebrew/lib',
                     'libdir=/usr/pkg/gcc16/../../outside'):
            with self.subTest(text=text):
                (self.lib / 'libgfortran.la').write_text(text)
                (self.lib / 'libgfortran.la').chmod(0o755)
                with self.assertRaisesRegex(SDKError, 'Build-host path'): self.inspect()
        (self.lib / 'libgfortran.la').write_text("libdir='/usr/pkg/gcc16/lib'\n")
        self.inspect()

    def test_generated_info_index_is_not_package_owned(self):
        info = self.root / 'usr/pkg/gcc16/share/info'
        info.mkdir(parents=True)
        (info / 'dir').write_text('generated index\n')
        result = self.inspect()
        self.assertEqual(result['generated'], ['usr/pkg/gcc16/share/info/dir'])
        self.assertNotIn('usr/pkg/gcc16/share/info/dir', result['devel'])


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + rest, verbosity=2)
