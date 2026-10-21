#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; independent synthetic ELF and receipt contracts.
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import os
import json
import shutil
import struct
import tarfile
import tempfile
import unittest
from unittest.mock import patch

FILES = Path(__file__).resolve().parents[1] / 'recipe/files'
sys.path.insert(0, str(FILES))
import sdk_source
ARGS = sdk_source.arguments(sys.argv[1:])
import runtime as rt
from emberbsd_sdk import inventory, jsonio


def elf(soname, machine=62, needed=('libc.so.12',), relro=True, kind=3, rpath='/usr/pkg/gcc16/lib',
        tls_symbols=None):
    strings = bytearray(b'\0')
    indexes = []
    for name in [soname] + list(needed) + [rpath]:
        indexes.append(len(strings))
        strings += name.encode() + b'\0'
    dynamic = [(5, 0x400200), (10, len(strings)), (14, indexes[0]), (29, indexes[-1])] + [(1, indexes[i + 1]) for i in range(len(needed))] + [(0, 0)]
    data = bytearray(512)
    data[:16] = b'\x7fELF\x02\x01\x01'.ljust(16, b'\0')
    data[16:64] = struct.pack('<HHIQQQIHHHHHH', kind, machine, 1, 0, 64, 0, 0, 64, 56, 3 if relro else 2, 0, 0, 0)
    entries = b''.join(struct.pack('<QQ', *entry) for entry in dynamic)
    total = 512 + len(strings)
    data[64:120] = struct.pack('<IIQQQQQQ', 1, 4, 0, 0x400000, 0x400000, total, total, 4096)
    data[120:176] = struct.pack('<IIQQQQQQ', 2, 4, 256, 0x400100, 0x400100, len(entries), len(entries), 8)
    if relro:
        data[176:232] = struct.pack('<IIQQQQQQ', 0x6474e552, 4, 256, 0x400100, 0x400100, len(entries), len(entries), 1)
    data[256:256+len(entries)] = entries
    data += strings
    if soname == 'libstdc++.so.7':
        symbols = tls_symbols if tls_symbols is not None else {
            '_ZSt11__once_call': 6, '_ZSt15__once_callable': 6, '__once_proxy': 2}
        names = bytearray(b'\0')
        entries = bytearray(24)
        for name, symbol_kind in symbols.items():
            entries += struct.pack('<IBBHQQ', len(names), 0x10 | symbol_kind, 0,
                                   3 if symbol_kind == 6 else 4, 0, 8)
            names += name.encode() + b'\0'
        strings_offset = len(data)
        data += names
        symbols_offset = len(data)
        data += entries
        section_offset = len(data)
        data += bytes(64)
        data += struct.pack('<IIQQQQIIQQ', 0, 3, 0, 0, strings_offset, len(names), 0, 0, 1, 0)
        data += struct.pack('<IIQQQQIIQQ', 0, 11, 0, 0, symbols_offset, len(entries), 1, 0, 8, 24)
        data += struct.pack('<IIQQQQIIQQ', 0, 8, 0x403, 0, 0, 16, 0, 0, 8, 0)
        data += struct.pack('<IIQQQQIIQQ', 0, 1, 6, 0, 0, 8, 0, 0, 4, 0)
        struct.pack_into('<Q', data, 40, section_offset)
        struct.pack_into('<HH', data, 58, 64, 5)
    return bytes(data)


class RuntimePackageTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='gcc-runtime-python-')).resolve()
        self.ownership_errors = []
        self.addCleanup(self.cleanup_work)
        run_logged = rt.process.run_logged
        def tracked_logged(*args, **kwargs):
            try:
                return run_logged(*args, **kwargs)
            except rt.ProcessOwnershipError as error:
                self.ownership_errors.append({'session': error.sid, 'reason': error.reason, 'log': error.log})
                jsonio.write_json(self.root / 'retained-ownership.json', self.ownership_errors, exclusive=not (self.root / 'retained-ownership.json').exists())
                raise
        tracker = patch.object(rt.process, 'run_logged', tracked_logged)
        tracker.start()
        self.addCleanup(tracker.stop)
        self.work, self.pkgsrc = self.root / 'work', self.root / 'pkgsrc'
        self.stage = self.work / 'stage'
        self.lib = self.stage / 'usr/pkg/gcc16/lib'
        self.lib.mkdir(parents=True)
        self.recipe = self.pkgsrc / 'lang/gcc16'
        (self.recipe / 'patches').mkdir(parents=True)
        for name in ('Makefile', 'Makefile.common', 'distinfo'):
            (self.recipe / name).write_text(name)
        self.archive = self.root / 'gcc.tar.xz'
        license_dir = self.root / 'gcc-16.2.0'
        license_dir.mkdir()
        for name in rt.LICENSES:
            (license_dir / name).write_text('License fixture: ' + name)
        with tarfile.open(self.archive, 'w:xz') as archive:
            archive.add(license_dir, arcname='gcc-16.2.0')
        self.target = 'amd64'
        self.selection = rt.SELECTIONS[0]
        # Independent synthetic math input bytes retain the production selection.
        self._old_math = dict(rt.MATH_PATCHES)
        self._old_tls = dict(rt.TLS_PATCHES)
        self.addCleanup(self.restore_math)
        for name in list(rt.MATH_PATCHES) + list(rt.TLS_PATCHES):
            (self.recipe / 'patches' / name).write_text('C++ capability input fixture: ' + name)
        rt.MATH_PATCHES = {name: rt.hash_file(self.recipe / 'patches' / name) for name in self._old_math}
        rt.TLS_PATCHES = {name: rt.hash_file(self.recipe / 'patches' / name) for name in self._old_tls}
        self.configure()

    def cleanup_work(self):
        if self.ownership_errors:
            print('Retained test work after an unproven producer drain: ' + str(self.root), file=sys.stderr)
        else:
            shutil.rmtree(self.root)

    def restore_math(self):
        rt.MATH_PATCHES = self._old_math
        rt.TLS_PATCHES = self._old_tls

    def configure(self, target='amd64', selection=None):
        self.target = target
        self.selection = selection or rt.SELECTIONS[0]
        triplet = rt.TARGETS[target]['triplet']
        machine = rt.TARGETS[target]['elf_machine']
        for path in self.lib.iterdir():
            path.unlink()
        (self.lib / 'libgcc_s.so.1').write_bytes(elf('libgcc_s.so.1', machine))
        (self.lib / 'libstdc++.so.7.36').write_bytes(elf('libstdc++.so.7', machine, ('libc.so.12', 'libgcc_s.so.1')))
        (self.lib / 'libstdc++.so.7').symlink_to('libstdc++.so.7.36')
        for name in self.selection.split(',')[2:]:
            soname = rt.LIBRARIES[name]
            (self.lib / soname).write_bytes(elf(soname, machine))
        header = self.stage / ('usr/pkg/gcc16/include/c++/' + triplet + '/bits/c++config.h')
        header.parent.mkdir(parents=True, exist_ok=True)
        header.write_text(''.join('#define _GLIBCXX_HAVE_' + name.upper() + ' 1\n' for name in rt.MATH_FUNCTIONS + ['tls']))
        (self.work / 'build-success').write_text('runtime-only-bootstrap\n')
        self.receipts()

    def receipts(self):
        recipe_files = [self.recipe / name for name in ('distinfo', 'Makefile', 'Makefile.common')] + sorted((self.recipe / 'patches').iterdir())
        content = 'scope=runtime-only-bootstrap\ntarget=' + self.target + '\ntriplet=' + rt.TARGETS[self.target]['triplet'] + '\nseed_source=' + 'a' * 40 + '\nruntime_libraries=' + self.selection + '\n'
        content += ''.join(rt.hash_file(path) + '  ' + str(path) + '\n' for path in [self.archive] + recipe_files)
        (self.work / 'inputs.txt').write_text(content)
        tree = inventory.snapshot_tree(self.stage)
        (self.work / 'stage.sha256').write_text(''.join(record['sha256'] + '  ./' + name + '\n' for name, record in tree.items() if record['kind'] == 'file'))
        (self.work / 'stage.symlinks').write_text(''.join('./' + name + '\t' + record['target'] + '\n' for name, record in tree.items() if record['kind'] == 'link'))

    def verifier(self, **kwargs):
        return rt.Stage(self.work, self.pkgsrc, self.archive, expected_source=rt.hash_file(self.archive), **kwargs)

    def test_tls_abi_symbols_and_table_bounds(self):
        path = self.lib / 'libstdc++.so.7.36'
        original = path.read_bytes()
        symbols = {'_ZSt11__once_call': 6, '_ZSt15__once_callable': 6, '__once_proxy': 2}
        for name in symbols:
            for change in ('missing', 'wrong-kind'):
                altered = dict(symbols)
                if change == 'missing':
                    del altered[name]
                else:
                    altered[name] = 1
                with self.subTest(name=name, change=change):
                    path.write_bytes(elf('libstdc++.so.7', tls_symbols=altered))
                    self.receipts()
                    with self.assertRaisesRegex(rt.Invalid, 'TLS ABI export'):
                        self.verifier().verify()
        for field, value in ((40, len(original) + 1), (58, 32), (60, 0)):
            altered = bytearray(original)
            struct.pack_into('<Q' if field == 40 else '<H', altered, field, value)
            path.write_bytes(altered)
            self.receipts()
            with self.assertRaisesRegex(rt.Invalid, 'TLS ABI'):
                self.verifier().verify()
        # Old global functor exports are optional, not a compatibility claim.
        symbols['_ZSt14__once_functor'] = 1
        path.write_bytes(elf('libstdc++.so.7', tls_symbols=symbols))
        self.receipts()
        result = self.verifier().verify()
        self.assertEqual(result['tls_abi']['legacy_exports'], ['_ZSt14__once_functor'])
        self.assertIn('not-qualified', result['tls_abi']['old_non_tls_consumer_compatibility'])

    def test_tls_abi_rejects_invalid_definitions(self):
        path = self.lib / 'libstdc++.so.7.36'
        original = path.read_bytes()
        sections = struct.unpack_from('<Q', original, 40)[0]
        symbols = struct.unpack_from('<Q', original, sections + 2 * 64 + 24)[0]
        mutations = (
            (symbols + 24, '<I', 0xffffffff),  # Invalid name offset.
            (symbols + 24 + 4, '<B', 6),       # Local symbol.
            (symbols + 24 + 5, '<B', 2),       # Hidden symbol.
            (symbols + 24 + 6, '<H', 0),       # Undefined symbol.
            (symbols + 24 + 6, '<H', 65535),   # Unsupported extended section.
            (sections + 3 * 64 + 8, '<Q', 3), # TLS symbol in a non-TLS section.
            (sections + 2 * 64 + 56, '<Q', 16), # Wrong dynamic entry size.
            (sections + 4, '<I', 11),         # Ambiguous dynamic table.
        )
        for offset, form, value in mutations:
            with self.subTest(offset=offset, value=value):
                altered = bytearray(original)
                struct.pack_into(form, altered, offset, value)
                path.write_bytes(altered)
                self.receipts()
                with self.assertRaisesRegex(rt.Invalid, 'TLS ABI'):
                    self.verifier().verify()

    def test_both_targets_and_all_library_selections(self):
        for target in rt.TARGETS:
            for selection in rt.SELECTIONS:
                with self.subTest(target=target, selection=selection):
                    self.configure(target, selection)
                    result = self.verifier().verify()
                    self.assertEqual(result['metadata']['GCC_RUNTIME_LIBRARIES'], selection)
                    self.assertEqual(result['metadata']['GCC_RUNTIME_TARGET'], target)
                    self.assertEqual(len(result['files']), 3 + len(selection.split(',')) - 2)

    def test_target_identity_mutations(self):
        original = (self.work / 'inputs.txt').read_text()
        for changed in [original + 'target=amd64\n', original.replace('x86_64--netbsd', 'aarch64--netbsd'), original.replace('target=amd64', 'target=unknown'), original + 'triplet=x86_64--netbsd\n', original.replace('seed_source=' + 'a'*40, 'seed_source=short')]:
            with self.subTest(changed=changed):
                (self.work / 'inputs.txt').write_text(changed)
                self.assertRaises(rt.Invalid, self.verifier().verify)
        (self.work / 'inputs.txt').write_text(original)

    def test_manifest_and_source_refusals(self):
        self.verifier().verify()
        for file in (self.work / 'stage.sha256', self.work / 'stage.symlinks', self.work / 'inputs.txt', self.recipe / 'distinfo'):
            original = file.read_bytes()
            file.unlink()
            self.assertRaises((rt.Invalid, OSError), self.verifier().verify)
            file.write_bytes(original)
        (self.lib / 'extra.so.1').write_text('extra')
        self.assertRaises(rt.Invalid, self.verifier().verify)
        (self.lib / 'extra.so.1').unlink()
        path = self.lib / 'libgcc_s.so.1'
        path.write_bytes(path.read_bytes() + b'changed')
        self.assertRaises(rt.Invalid, self.verifier().verify)

    def test_tls_capability_and_inputs(self):
        result = self.verifier().verify()
        self.assertIn('GCC_RUNTIME_CXX_TLS_INPUTS_SHA256', result['metadata'])
        header = self.stage / ('usr/pkg/gcc16/include/c++/' + rt.TARGETS[self.target]['triplet'] + '/bits/c++config.h')
        original = header.read_text()
        for changed in (original.replace('#define _GLIBCXX_HAVE_TLS 1\n', ''), original + '#define _GLIBCXX_HAVE_TLS 1\n'):
            with self.subTest(header=changed[-40:]):
                header.write_text(changed)
                self.receipts()
                with self.assertRaisesRegex(rt.Invalid, 'TLS capability'):
                    self.verifier().verify()
        header.write_text(original)
        for name in rt.TLS_PATCHES:
            with self.subTest(patch=name):
                patch = self.recipe / 'patches' / name
                patch_bytes = patch.read_bytes()
                patch.write_bytes(patch_bytes + b'changed')
                self.receipts()
                with self.assertRaisesRegex(rt.Invalid, 'TLS source input'):
                    self.verifier().verify()
                patch.write_bytes(patch_bytes)
        self.receipts()
        self.verifier().verify()

    def test_wrong_elf_policy_after_rehash(self):
        for target in rt.TARGETS:
            self.configure(target)
            for kwargs in [dict(machine=183 if target == 'amd64' else 62), dict(kind=2), dict(relro=False), dict(needed=('libstdc++.so.6',)), dict(rpath='/tmp/host'), dict(soname='libgcc_s.so.2')]:
                with self.subTest(target=target, kwargs=kwargs):
                    values = dict(soname='libgcc_s.so.1', machine=rt.TARGETS[target]['elf_machine'])
                    values.update(kwargs)
                    (self.lib / 'libgcc_s.so.1').write_bytes(elf(**values))
                    self.receipts()
                    self.assertRaises(rt.Invalid, self.verifier().verify)
            self.configure(target)

    def test_optional_missing_foreign_and_dependency(self):
        for target in rt.TARGETS:
            self.configure(target, rt.SELECTIONS[-1])
            (self.lib / 'libgomp.so.1').unlink()
            self.receipts()
            self.assertRaises(rt.Invalid, self.verifier().verify)
            self.configure(target)
            (self.lib / 'libatomic.so.3').write_bytes(elf('libatomic.so.3', rt.TARGETS[target]['elf_machine']))
            self.receipts()
            self.assertRaises(rt.Invalid, self.verifier().verify)
            self.configure(target)
            (self.lib / 'libgcc_s.so.1').write_bytes(elf('libgcc_s.so.1', rt.TARGETS[target]['elf_machine'], ('libatomic.so.3',)))
            self.receipts()
            self.assertRaises(rt.Invalid, self.verifier().verify)

    def test_alias_inventory_and_escape(self):
        alias = self.lib / 'libstdc++.so.7'
        alias.unlink()
        alias.symlink_to('/etc/passwd')
        self.assertRaises(rt.Invalid, self.verifier().verify)
        alias.unlink()
        alias.symlink_to('intermediate')
        (self.lib / 'intermediate').symlink_to('libstdc++.so.7.36')
        self.receipts()
        self.assertRaises(rt.Invalid, self.verifier().verify)

    def test_library_claims(self):
        inputs = self.work / 'inputs.txt'
        original = inputs.read_text()
        for choice in ['libstdc++,libgcc', 'libgcc,libstdc++,libgcc', 'libgcc,libstdc++,unknown', 'libgcc,libstdc++\nruntime_libraries=libgcc,libstdc++', 'libgcc,libstdc++\x00']:
            inputs.write_text(original.replace('runtime_libraries=' + self.selection + '\n', 'runtime_libraries=' + choice + '\n'))
            self.assertRaises(rt.Invalid, self.verifier().verify)
        inputs.write_text(original.replace('runtime_libraries=' + self.selection + '\n', '') + 'runtime_libraries=' + self.selection)
        self.assertRaises(rt.Invalid, self.verifier().verify)
        inputs.write_text(original.replace('runtime_libraries=' + self.selection + '\n', ''))
        self.verifier().verify()

    def test_quarantined_stage_cannot_be_packaged(self):
        stage = self.verifier()
        (self.work / rt.sdk_source.PRODUCER_QUARANTINE).write_text('{}\n')
        self.assertRaisesRegex(rt.Invalid, 'shutdown is unproven', stage.verify)

    def test_historical_cannot_install(self):
        # Old authenticated parents remain usable for provenance, never install.
        (self.lib / 'libstdc++.so.7.36').write_bytes(elf(
            'libstdc++.so.7', needed=('libc.so.12', 'libgcc_s.so.1'),
            tls_symbols={'_ZSt14__once_functor': 1, '__once_proxy': 2}))
        self.receipts()
        with self.assertRaisesRegex(rt.Invalid, 'TLS ABI export'):
            self.verifier().verify()
        header = self.stage / ('usr/pkg/gcc16/include/c++/' +
                               rt.TARGETS[self.target]['triplet'] + '/bits/c++config.h')
        header.write_text(header.read_text().replace('#define _GLIBCXX_HAVE_TLS 1\n', ''))
        self.receipts()
        self.verifier(historical=True).verify()
        self.assertRaises(rt.Invalid, self.verifier(historical=True).install, self.root / 'dest')

    def test_install_payload_and_ownership(self):
        destination = self.root / 'dest'
        result = self.verifier().install(destination)
        self.assertEqual(result, self.verifier().verify())
        self.assertTrue((destination / 'usr/pkg/share/licenses/gcc16-runtime/COPYING3').is_file())
        self.assertFalse((destination / 'usr/pkg/gcc16/include').exists())
        self.assertRaises(rt.Invalid, self.verifier().install, destination)
        self.assertIn('@pkgcfl gcc16<16.2.0nb5', rt.plist(result))
        self.assertNotIn('@pkgcfl gcc16-[0-9]*', rt.plist(result))

    def test_pkgtools_calendar(self):
        for value in ('20260229', '20261301', '20260001', '20260100', '00000101', 'nb4', '20260101\n', None):
            self.assertRaises(rt.Invalid, rt.validate_pkgtools_version, value)
        self.assertEqual(rt.validate_pkgtools_version('20240229'), '20240229')

    def external_receipts(self):
        (self.work / 'build-success').write_text('runtime-only-external-compiler\n')
        prefix = '/fixture/compiler'
        triplet = rt.TARGETS[self.target]['triplet']
        receipt = 'compiler_mode=external-posix\nversion=16.2.0\ntriplet=' + triplet + '\nthread_model=posix\nsupport_target=gcc-leaf-metadata-v1\ntarget_objects=external-compiler\ncompiler=' + prefix + '\ncc1=' + prefix + '/libexec/cc1\ncc1plus=' + prefix + '/libexec/cc1plus\n'
        receipt += ''.join('a'*64 + '  ' + path + '\n' for path in [prefix+'/bin/'+triplet+'-gcc',prefix+'/bin/'+triplet+'-g++',prefix+'/libexec/cc1',prefix+'/libexec/cc1plus'])
        command=prefix+'/bin/'+triplet+'-gcc --sysroot=/fixture/seed -B/fixture/work/build/gcc/'
        plan='support_target=gcc-leaf-metadata-v1\ntarget_objects=external-compiler\nCC='+command+'\nCXX='+command+' -shared-libgcc -nostdinc++\n'
        (self.work/'external-compiler.txt').write_text(receipt)
        (self.work/'external-runtime-plan.txt').write_text(plan)
        (self.work/'external-support').mkdir(exist_ok=True)
        documents=[self.work/'external-compiler.txt',self.work/'external-runtime-plan.txt']
        for name in 'libgcc.mvars specs tconfig.h version.h auto-host.h Makefile config.status'.split():
            path=self.work/'external-support'/name;path.write_text('generated support fixture');documents.append(path)
        inputs=(self.work/'inputs.txt').read_text().replace('scope=runtime-only-bootstrap','scope=runtime-only-external-compiler')+'sysroot=/fixture/seed\n'
        inputs+=''.join(rt.hash_file(path)+'  '+str(path)+'\n' for path in documents)
        (self.work/'inputs.txt').write_text(inputs)
        return inputs,receipt,plan

    def test_external_receipt_mutations(self):
        for target in rt.TARGETS:
            self.configure(target)
            inputs,receipt,plan=self.external_receipts()
            self.verifier().verify()
            for changed in [receipt.replace('thread_model=posix','thread_model=single'),receipt.replace('gcc-leaf-metadata-v1','libgcc-support'),receipt.replace('/libexec/cc1plus','/../cc1plus')]:
                (self.work/'external-compiler.txt').write_text(changed)
                # A rehashed invalid contract must still fail.
                (self.work/'inputs.txt').write_text(inputs.replace(rt.hashlib.sha256(receipt.encode()).hexdigest(),rt.hashlib.sha256(changed.encode()).hexdigest()))
                self.assertRaises(rt.Invalid,self.verifier().verify)
            (self.work/'external-compiler.txt').write_text(receipt)
            changed=plan.replace('/fixture/seed','/foreign/seed')
            (self.work/'external-runtime-plan.txt').write_text(changed)
            (self.work/'inputs.txt').write_text(inputs.replace(rt.hashlib.sha256(plan.encode()).hexdigest(),rt.hashlib.sha256(changed.encode()).hexdigest()))
            self.assertRaises(rt.Invalid,self.verifier().verify)
            (self.work/'external-runtime-plan.txt').write_text(plan)
            (self.work/'inputs.txt').write_text(inputs)
            (self.work/'external-support/specs').write_text('mutated')
            self.assertRaises(rt.Invalid,self.verifier().verify)

    def test_malformed_relro_dynamic_and_tags(self):
        original=elf('libgcc_s.so.1')
        mutations=[]
        for field_,value in [(176+40,0),(176+16,0x900000)]:
            data=bytearray(original);struct.pack_into('<Q',data,field_,value);mutations.append(bytes(data))
        data=bytearray(original);struct.pack_into('<Q',data,256+16*3,14);mutations.append(bytes(data))
        data=bytearray(original);data[256+16*5:256+16*6]=struct.pack('<QQ',1,0);mutations.append(bytes(data))
        for data in mutations:
            (self.lib/'libgcc_s.so.1').write_bytes(data);self.receipts()
            self.assertRaises(rt.Invalid,self.verifier().verify)

    def test_unproven_package_shutdown_retains_work(self):
        executable=self.root/'pkg-create'
        executable.write_text('#!/bin/sh\necho 20260227\n')
        executable.chmod(0o755)
        temporary=self.root/'quarantine-work';temporary.mkdir()
        output=self.root/'quarantine-output'
        with patch.object(rt.tempfile,'mkdtemp',return_value=str(temporary)), patch.object(rt.process,'run_logged',side_effect=rt.ProcessOwnershipError(1, 'owned producer stop unproven')):
            with self.assertRaisesRegex(rt.Invalid,'shutdown is unproven'):
                rt.create(self.verifier(),str(executable),str(output))
        self.assertTrue(output.is_dir())
        self.assertTrue((temporary/'PLIST').is_file())
        self.assertTrue((temporary/'payload/usr/pkg/gcc16/lib/libgcc_s.so.1').is_file())

    def stage_manifests(self, work):
        tree=inventory.snapshot_tree(Path(work)/'stage')
        (Path(work)/'stage.sha256').write_text(''.join(record['sha256']+'  ./'+name+'\n' for name,record in tree.items() if record['kind']=='file'))
        (Path(work)/'stage.symlinks').write_text(''.join('./'+name+'\t'+record['target']+'\n' for name,record in tree.items() if record['kind']=='link'))

    def rebuild_fixture(self):
        import inheritance as inh
        self.configure('aarch64',rt.SELECTIONS[-1])
        for family,soname in [('libgomp','libgomp.so.1'),('libatomic','libatomic.so.3')]:
            (self.lib/soname).rename(self.lib/(soname+'.0'))
            (self.lib/soname).symlink_to(soname+'.0')
        (self.stage/'usr/pkg/gcc16/include/c++/vector').write_text('C++ header fixture')
        for name in inh.CRT_FILES:
            path=self.lib/'gcc/aarch64--netbsd/16.2.0'/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('Synthetic CRT/support receipt fixture: '+name)
        (self.recipe/'Makefile').write_text('PKGREVISION=\t1\n')
        self.receipts()
        parent=self.verifier().verify()
        work=self.root/'rebuild';work.mkdir()
        shutil.copytree(self.work,work/'parent',symlinks=True)
        shutil.copytree(self.pkgsrc,work/'parent-recipe',symlinks=True)
        new_recipe=self.root/'new-recipe'
        shutil.copytree(self.pkgsrc,new_recipe,symlinks=True)
        outer=(Path(__file__).resolve().parents[2]/'patches/gcc-netbsd-locale.patch').read_text()
        body=outer.split('+++ b/lang/gcc16/patches/'+inh.PATCH+'\n',1)[1].splitlines(keepends=True)[1:]
        self.assertTrue(all(line.startswith('+') for line in body))
        patch_bytes=''.join(line[1:] for line in body).encode()
        (new_recipe/'lang/gcc16/patches'/inh.PATCH).write_bytes(patch_bytes)
        self.assertEqual(rt.hash_file(new_recipe/'lang/gcc16/patches'/inh.PATCH),inh.PATCH_SHA256)
        (new_recipe/'lang/gcc16/Makefile').write_text('PKGREVISION=\t2\n')
        digest=rt.hashlib.sha1(b''.join(line for line in patch_bytes.splitlines(keepends=True) if b'$NetBSD' not in line)).hexdigest()
        (new_recipe/'lang/gcc16/distinfo').write_text('SHA1 ('+inh.PATCH+') = '+digest+'\n'+(self.recipe/'distinfo').read_text())
        shutil.copytree(self.stage,work/'stage',symlinks=True)
        with (work/'stage/usr/pkg/gcc16/lib/libstdc++.so.7.36').open('ab') as stream:stream.write(b'Fresh synthetic ELF receipt fixture')
        (work/'stage/usr/pkg/gcc16/include/c++/aarch64--netbsd/bits/c++locale.h').write_text('fresh header fixture')
        all_=inh.inventory(work/'stage')
        old=inh.inventory(work/'parent/stage')
        inherited={path:old[path] for path in inh.inherited_paths(parent)}
        fresh={path:record for path,record in all_.items() if path not in inherited}
        logs={}
        for name in ('configure.log','runtime-build.log','runtime-install.log'):
            (work/name).write_text('Synthetic log fixture. No actual build.')
            logs[name]=rt.hash_file(work/name)
        configuration={}
        for name in inh.CONFIG_FILES:
            path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('Synthetic configuration fixture')
            configuration[name]=rt.hash_file(path)
        receipt={'format':1,'parent_paths':{'archive':str(self.archive),'pkgsrc':str(self.pkgsrc)},'parent_receipts':{name:rt.hash_file(work/'parent'/name) for name in inh.PARENT_FILES},'inherited':inherited,'rebuilt':fresh,'build_logs':logs,'configuration':configuration}
        rt.jsonio.write_json(work/'inheritance.json',receipt)
        files=[self.archive,work/'inheritance.json']+[work/name for name in inh.CONFIG_FILES]+[new_recipe/'lang/gcc16'/name for name in ('Makefile','Makefile.common','distinfo')]+sorted((new_recipe/'lang/gcc16/patches').iterdir())
        inputs='scope=runtime-libstdcxx-rebuild\ntarget=aarch64\ntriplet=aarch64--netbsd\nseed_source='+'a'*40+'\nruntime_libraries='+self.selection+'\n'
        (work/'inputs.txt').write_text(inputs+''.join(rt.hash_file(path)+'  '+str(path)+'\n' for path in files))
        (work/'build-success').write_text('runtime-libstdcxx-rebuild\n')
        self.stage_manifests(work)
        return rt.Stage(work,new_recipe,self.archive,expected_source=rt.hash_file(self.archive)),work,new_recipe

    def test_rebuild_parent_and_component_mutations(self):
        import inheritance as inh
        stage,work,recipe=self.rebuild_fixture()
        result=stage.verify()
        self.assertEqual(result['metadata']['GCC_RUNTIME_BUILD_MODE'],'standalone-libstdcxx')
        self.assertEqual(len(result['files']),7)
        self.assertEqual((work/'parent/inputs.txt').read_bytes(),(self.work/'inputs.txt').read_bytes())
        files=[work/'parent/inputs.txt',work/'parent/stage/usr/pkg/gcc16/lib/libgcc_s.so.1',work/'parent-recipe/lang/gcc16/Makefile.common',recipe/'lang/gcc16/patches'/inh.PATCH,recipe/'lang/gcc16/Makefile.common',work/'stage/usr/pkg/gcc16/lib/libgcc_s.so.1',work/'stage/usr/pkg/gcc16/include/c++/vector',work/'runtime-build.log',work/'configuration/config.h',work/'inheritance.json',work/'build-success',work/'parent/build-success']
        for path in files:
            with self.subTest(path=path):
                original=path.read_bytes();path.write_text('{}' if path.suffix=='.json' else 'changed')
                self.assertRaises(rt.Invalid,stage.verify)
                path.write_bytes(original)

    def test_rebuild_rehashed_false_ownership_and_old_dso(self):
        stage,work,recipe=self.rebuild_fixture()
        original_receipt=(work/'inheritance.json').read_bytes()
        original_inputs=(work/'inputs.txt').read_text()
        target=work/'stage/usr/pkg/gcc16/lib/libstdc++.so.7.36'
        original_dso=target.read_bytes()
        import inheritance as inh
        for mutation in ('missing-component','old-dso','inherited-bytes'):
            with self.subTest(mutation=mutation):
                receipt=rt.jsonio.loads_json(original_receipt)
                if mutation=='missing-component':
                    receipt['inherited'].pop('usr/pkg/gcc16/lib/libgcc_s.so.1')
                elif mutation=='old-dso':
                    target.write_bytes((work/'parent/stage/usr/pkg/gcc16/lib/libstdc++.so.7.36').read_bytes())
                    receipt['rebuilt']['usr/pkg/gcc16/lib/libstdc++.so.7.36']=inh.inventory(work/'stage')['usr/pkg/gcc16/lib/libstdc++.so.7.36']
                else:
                    path=work/'stage/usr/pkg/gcc16/lib/libgcc_s.so.1';path.write_bytes(path.read_bytes()+b'changed')
                rt.jsonio.write_json(work/'inheritance.json',receipt,exclusive=False)
                (work/'inputs.txt').write_text(original_inputs.replace(rt.hashlib.sha256(original_receipt).hexdigest(),rt.hash_file(work/'inheritance.json')))
                self.stage_manifests(work)
                self.assertRaises(rt.Invalid,stage.verify)
                (work/'inheritance.json').write_bytes(original_receipt);(work/'inputs.txt').write_text(original_inputs);target.write_bytes(original_dso)
                (work/'stage/usr/pkg/gcc16/lib/libgcc_s.so.1').write_bytes((work/'parent/stage/usr/pkg/gcc16/lib/libgcc_s.so.1').read_bytes())
                self.stage_manifests(work)

    def test_relink_rehashed_command_parent_and_ownership_mutations(self):
        import relro
        locale,parent,recipe=self.rebuild_fixture()
        locale.verify()
        work=self.root/'relink';(work/'proof').mkdir(parents=True)
        shutil.copytree(parent/'stage',work/'stage',symlinks=True)
        backup=work/'backup';backup.write_text('Synthetic archived input. No actual compiler build.')
        commands=[];components={}
        for library,name in relro.COMPONENTS.items():
            relative='usr/pkg/gcc16/lib/'+name
            before,after=work/'proof'/(name+'.baseline'),work/'proof'/(name+'.relro')
            shutil.copyfile(parent/'stage'/relative,before)
            after.write_bytes(before.read_bytes()+b'Synthetic relink fixture')
            shutil.copyfile(after,work/'stage'/relative)
            components[library]={'path':relative,'before':rt.hash_file(before),'after':rt.hash_file(after)}
            commands += [{'component':library,'argv':['/fixture/xgcc','-shared','-o',str(before)],'status':0},{'component':library,'argv':['/fixture/xgcc','-shared','-o',str(after),'-Wl,-z,relro'],'status':0}]
        rt.jsonio.write_json(work/'commands.json',commands)
        receipt={'format':1,'parent_work':str(parent),'parent_receipts':{name:rt.hash_file(parent/name) for name in relro.PARENT},'backup':{'path':str(backup),'sha256':rt.hash_file(backup)},'inputs':{str(work/'commands.json'):rt.hash_file(work/'commands.json')},'components':components}
        rt.jsonio.write_json(work/'relink.json',receipt)
        base_inputs=(parent/'inputs.txt').read_text().replace('scope=runtime-libstdcxx-rebuild','scope=runtime-relro-relink')
        def repin():
            (work/'inputs.txt').write_text(base_inputs+rt.hash_file(work/'relink.json')+'  '+str(work/'relink.json')+'\n')
            self.stage_manifests(work)
        repin();(work/'build-success').write_text('runtime-relro-relink\n')
        stage=rt.Stage(work,recipe,self.archive,expected_source=rt.hash_file(self.archive))
        self.assertEqual(stage.verify()['metadata']['GCC_RUNTIME_BUILD_MODE'],'libstdcxx-and-runtime-relro-relink')
        for path in [parent/'build-success',backup,work/'proof/libgcc_s.so.1.baseline',work/'proof/libgcc_s.so.1.relro',work/'stage/usr/pkg/gcc16/include/c++/vector']:
            original=path.read_bytes();path.write_text('changed');repin()
            self.assertRaises(rt.Invalid,stage.verify)
            path.write_bytes(original);repin()
        original=rt.jsonio.read_json(work/'relink.json')
        for mutation in ('selection','relative-input','command'):
            changed=rt.jsonio.loads_json(json.dumps(original))
            if mutation=='selection':changed['components'].pop('libatomic')
            elif mutation=='relative-input':changed['inputs']={'commands.json':rt.hash_file(work/'commands.json')}
            else:
                values=rt.jsonio.read_json(work/'commands.json');values[1]['argv'].append('-Wl,-z,now')
                rt.jsonio.write_json(work/'commands.json',values,exclusive=False);changed['inputs'][str(work/'commands.json')]=rt.hash_file(work/'commands.json')
            rt.jsonio.write_json(work/'relink.json',changed,exclusive=False);repin()
            self.assertRaises(rt.Invalid,stage.verify)
            rt.jsonio.write_json(work/'commands.json',commands,exclusive=False)

    def test_real_native_packages(self):
        executable = os.environ.get('PKG_CREATE')
        if not executable:
            self.skipTest('Set PKG_CREATE to native host pkg_create')
        for target in rt.TARGETS:
            for selection in (rt.SELECTIONS[0], rt.SELECTIONS[-1]):
                self.configure(target, selection)
                output = self.root / (target + '-' + str(len(selection)))
                rt.create(self.verifier(), executable, output)
                self.assertTrue((output / (rt.NAME + '.tgz')).is_file())
                pkg_add = os.environ.get('PKG_ADD')
                if pkg_add:
                    destination = self.root / (target + '-installed-' + str(len(selection)))
                    destination.mkdir()
                    added = rt.process.capture([pkg_add, '-I', '-K', '/usr/pkg/pkgdb', '-P', str(destination), '-m', 'NetBSD/' + rt.TARGETS[target]['machine_arch'] + ' 11.0', str(output / (rt.NAME + '.tgz'))])
                    self.assertNotIn(b'PKGTOOLS_VERSION', added.stderr)
                    for name in self.verifier().verify()['files']:
                        expected, installed = self.stage / 'usr/pkg' / name, destination / 'usr/pkg' / name
                        if expected.is_symlink():
                            self.assertEqual(os.readlink(installed), os.readlink(expected))
                        else:
                            self.assertEqual(rt.hash_file(installed), rt.hash_file(expected))

                self.assertRaises(rt.Invalid, rt.create, self.verifier(), executable, output)


if __name__ == '__main__':
    sdk_source.install_signal_handlers()
    unittest.main(argv=[sys.argv[0]] + ARGS)
