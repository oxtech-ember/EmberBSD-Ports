#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; causal host controller regression fixtures.
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib
import os
import shutil
import struct
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PROFILE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
import sdk_source
ARGS = sdk_source.arguments(sys.argv[1:])
for path in (PROFILE, PROFILE / 'bootstrap', PROFILE / 'cross'):
    sys.path.insert(0, str(path))
import host
from emberbsd_sdk.errors import SDKError
from emberbsd_sdk import inventory, jsonio
from target_options import parse
from runtime import field
from runtime_libraries import selected, check_prior, verify_completed_stage
from resume_state import backup_resume, check_resume, verify_frontend, verify_hash_rows
from support_resume import support
from external_compiler import build_external
from libstdcxx import LibstdcxxRebuild
# Load the bootstrap producer separately from cross/pipeline.py.
import importlib.util
spec = importlib.util.spec_from_file_location('bootstrap_pipeline', PROFILE / 'bootstrap/pipeline.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class ControllerTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='gcc-python-controllers-')).resolve()
        self.ownership_errors = []
        self.addCleanup(self.cleanup_work)
        run_logged = host.process.run_logged
        def tracked_logged(*args, **kwargs):
            try:
                return run_logged(*args, **kwargs)
            except host.ProcessOwnershipError as error:
                self.ownership_errors.append({'session': error.sid, 'reason': error.reason, 'log': error.log})
                jsonio.write_json(self.root / 'retained-ownership.json', self.ownership_errors, exclusive=not (self.root / 'retained-ownership.json').exists())
                raise
        tracker = patch.object(host.process, 'run_logged', tracked_logged)
        tracker.start()
        self.addCleanup(tracker.stop)
        self.pkgsrc = self.root / 'pkgsrc'
        self.recipe = self.pkgsrc / 'lang/gcc16'
        (self.recipe / 'patches').mkdir(parents=True)
        self.archive = self.root / 'gcc.tar'
        self.archive.write_bytes(b'Pinned source fixture')
        self.expected = inventory.sha256_file(self.archive)
        self.source_patch = self.recipe / 'patches/patch-gcc_cp_module.cc'
        self.source_patch.write_text('modules repair fixture\n')
        self.distinfo()
        (self.recipe / 'Makefile').write_text("CONFIGURE_ARGS+= --disable-libssp\nSUBST_SED.libstdc= -e 's,libtool_VERSION=6:,libtool_VERSION=7:,g'\n")
        (self.recipe / 'Makefile.common').write_text('common fixture')
        self.kernel, self.seed, self.math = [self.root / name for name in ('kernel', 'seed', 'math')]
        (self.kernel / 'bin').mkdir(parents=True)
        (self.kernel / 'libexec').mkdir()
        self.make = self.root / 'gmake'
        self.executable(self.make, "case \"$1\" in --version) echo 'GNU Make 4.4.1';; *) exit 97;; esac\n")
        (self.seed / 'usr/include').mkdir(parents=True)
        (self.seed / 'usr/lib').mkdir()
        for name in ('stddef.h', 'stdio.h', 'pthread.h', 'math.h'):
            (self.seed / 'usr/include' / name).write_text('header fixture\n')
        (self.math / 'include').mkdir(parents=True)
        (self.math / 'lib').mkdir()
        definitions = {'gmp': [('__GNU_MP_VERSION',6),('__GNU_MP_VERSION_MINOR',3),('__GNU_MP_VERSION_PATCHLEVEL',0)], 'mpfr': [('MPFR_VERSION_MAJOR',4),('MPFR_VERSION_MINOR',2),('MPFR_VERSION_PATCHLEVEL',2)], 'mpc': [('MPC_VERSION_MAJOR',1),('MPC_VERSION_MINOR',4),('MPC_VERSION_PATCHLEVEL',1)]}
        for name, macros in definitions.items():
            (self.math / 'lib' / ('lib'+name+'.a')).write_text('static archive fixture')
            (self.math / 'include' / (name+'.h')).write_text(''.join('#define '+macro+' '+str(value)+'\n' for macro,value in macros))
        self.env = patch.dict(os.environ, {'CROSS_JOBS': '2', 'EMBERBSD_SYSROOT_SOURCE': 'a'*40, 'GNU_MAKE': str(self.make)}, clear=False)
        self.env.start();self.addCleanup(self.env.stop)
        self.row_patch = patch.object(host, 'source_row', return_value=['gcc','16.2.0','fixture',self.expected])
        self.row_patch.start();self.addCleanup(self.row_patch.stop)
        self.configure('amd64')

    def cleanup_work(self):
        if self.ownership_errors:
            print('Retained test work after an unproven producer drain: ' + str(self.root), file=sys.stderr)
        else:
            shutil.rmtree(self.root)

    def executable(self, path, script):
        Path(path).write_text('#!/bin/sh\nset -eu\n'+script)
        Path(path).chmod(0o755)

    def distinfo(self):
        self.recipe.joinpath('distinfo').write_text(''.join('SHA1 ('+path.name+') = '+hashlib.sha1(b''.join(line for line in path.read_bytes().splitlines(keepends=True) if b'$NetBSD' not in line)).hexdigest()+'\n' for path in sorted(self.recipe.joinpath('patches').iterdir())))

    def configure(self, target):
        self.target=target
        triplet,machine,arch,_ = host.TARGETS[target]
        compiler = '''case "$1" in
-dumpmachine) echo TRIPLET;;
-dumpfullversion) echo16.2.0;;
--version) echo 'gcc (GCC)16.2.0';;
-v) echo 'Thread model: posix' >&2;;
-print-prog-name=*) echo 'PREFIX/libexec/'"${1#*=}";;
-dM) cat >/dev/null; printf '%s\\n' '#define __GNUC__16' '#define __NetBSD__1' '#define __SIZEOF_POINTER__8' '#define ARCH1';;
*) exit99;; esac
'''.replace('echo16','echo 16').replace('GCC)16','GCC) 16').replace('__GNUC__16','__GNUC__ 16').replace('__NetBSD__1','__NetBSD__ 1').replace('__SIZEOF_POINTER__8','__SIZEOF_POINTER__ 8').replace('ARCH1',arch+' 1').replace('TRIPLET',triplet).replace('PREFIX',str(self.kernel)).replace('exit99','exit 99')
        for name in ('gcc','g++'):
            self.executable(self.kernel/'bin'/(triplet+'-'+name),compiler)
        for name in ('cc1','cc1plus'):
            self.executable(self.kernel/'libexec'/name,'exit 0\n')
        for name in host.TOOLS:
            label='assembler' if name=='as' else name
            self.executable(self.kernel/'bin'/(triplet+'-'+name),"echo 'GNU "+label+" (fixture)2.47'\n"+("echo 'This assembler was configured for a target of "+triplet+"'\n" if name=='as' else ''))
        header=b'\x7fELF\x02\x01\x01'.ljust(16,b'\0')+struct.pack('<HHIQQQIHHHHHH',3,machine,1,0,64,0,0,64,56,0,0,0,0)
        for name in ('libc.so.12','libpthread.so.1','libm.so.0','crt0.o'):
            (self.seed/'usr/lib'/name).write_bytes(header)
        self.kernel.parent.joinpath('inputs.txt').write_text('mode=kernel\n'+self.expected+'  source\n'+inventory.sha256_file(self.recipe/'distinfo')+'  distinfo\n')

    def state(self, *options):
        args=['--check']+list(options)+['--target',self.target,str(self.pkgsrc),str(self.archive),str(self.kernel),str(self.seed),str(self.math),str(self.root/'output')]
        return bootstrap.Bootstrap(args)

    def test_unproven_drain_persists_and_blocks_all_resume_modes(self):
        work = self.root / 'output'
        work.mkdir()
        (work / 'retained.o').write_bytes(b'original object')
        state = SimpleNamespace(work=work)
        with patch.object(host.process, 'run_logged', side_effect=host.ProcessOwnershipError(1, 'injected ownership failure')):
            self.assertRaises(host.ProcessOwnershipError, bootstrap.Bootstrap.run_logged, state, ['/unexecuted-fixture'], work / 'producer.log')
        marker = work / host.QUARANTINE
        self.assertTrue(marker.is_file())
        self.assertEqual((work / 'retained.o').read_bytes(), b'original object')
        for options in (('--resume',), ('--resume-runtime',), ('--external-compiler', '--resume-support')):
            with self.subTest(options=options):
                self.assertRaisesRegex(SDKError, 'shutdown is unproven', self.state, *options)
        for function in (check_resume, backup_resume):
            self.assertRaisesRegex(SDKError, 'shutdown is unproven', function, state)
        for action in ('checkpoint', 'check', 'resume'):
            self.assertRaisesRegex(SDKError, 'shutdown is unproven', support, action, work)
        self.assertRaisesRegex(SDKError, 'shutdown is unproven', host.logged, ['/unexecuted-fixture'], work / 'next.log', quarantine=work)
        # Explicit fixture recovery removes the marker. Commands do not remove it.
        marker.unlink()
        self.executable(self.make, 'exit 97\n')
        with self.assertRaises(SDKError) as failed:
            bootstrap.Bootstrap.run_logged(state, [self.make], work / 'failure.log')
        self.assertEqual(failed.exception.returncode, 97)
        self.assertFalse(marker.exists())
        host.assert_recoverable(work)
        marker.symlink_to('missing-marker-target')
        self.assertRaisesRegex(SDKError, 'shutdown is unproven', host.assert_recoverable, work)

    def test_both_architecture_preflight_and_no_output(self):
        for target in host.TARGETS:
            self.configure(target)
            for options in ((),('--external-compiler',)):
                with self.subTest(target=target,options=options):
                    self.state(*options).preflight()
                    self.assertFalse((self.root/'output').exists())
        # Real sysroots use relative links for several headers.
        header=self.seed/'usr/include/stddef.h';header.unlink();header.symlink_to('stdio.h')
        self.state('--external-compiler').preflight()

    def test_wrong_target_seed_source_and_tool_identity(self):
        state=self.state()
        (self.seed/'usr/lib/libc.so.12').write_text('not ELF')
        self.assertRaises(SDKError,state.preflight)
        self.configure('amd64')
        self.source_patch.write_text('changed')
        self.assertRaises(SDKError,self.state().preflight)
        self.source_patch.write_text('modules repair fixture\n')
        tool=self.kernel/'bin/x86_64--netbsd-nm'
        self.executable(tool,"echo 'GNU ar (wrong tool)'\n")
        self.assertRaises(SDKError,self.state().preflight)
        self.assertFalse((self.root/'output').exists())

    def test_target_options_and_worker_refusals(self):
        self.assertEqual(parse([]),('aarch64','applications',[]))
        self.assertEqual(parse(['--target','amd64','--kernel','a'],True),('amd64','kernel',['a']))
        for args in (['--target'],['--target','amd64','--target','amd64'],['--target','riscv64'],['--kernel'],['--unknown']):
            self.assertRaises(SDKError,parse,args)
        for value in ('0','00','-1','no',''):
            with patch.dict(os.environ,{'CROSS_JOBS':value}):
                self.assertRaises(SDKError,host.jobs)
        self.assertRaises(SDKError,self.state('--external-compiler','--with-libgomp').preflight)

    def test_bootstrap_libgcc_requires_explicit_kernel_mode(self):
        for options in (['--kernel', '--bootstrap-libgcc'],
                        ['--bootstrap-libgcc', '--target', 'aarch64', '--kernel']):
            self.assertEqual(parse(options, True, True), ('aarch64', 'kernel-bootstrap', []))
        for options in (['--bootstrap-libgcc'],
                        ['--kernel', '--bootstrap-libgcc', '--bootstrap-libgcc'],
                        ['--kernel', '--kernel', '--bootstrap-libgcc'],
                        ['--kernel', '--bootstrap-libgcc', '--target', 'unknown']):
            self.assertRaises(SDKError, parse, options, True, True)
        self.assertRaises(SDKError, parse, ['--kernel', '--bootstrap-libgcc'], True)
        self.assertRaises(SDKError, parse, ['--bootstrap-libgcc'], False, True)
        spec_ = importlib.util.spec_from_file_location('cross_pipeline', PROFILE / 'cross/pipeline.py')
        cross = importlib.util.module_from_spec(spec_)
        spec_.loader.exec_module(cross)
        self.assertRaisesRegex(SDKError, 'Usage:', cross.build_main,
            ['--kernel', '--bootstrap-libgcc', str(self.pkgsrc), str(self.archive),
             str(self.root / 'tools'), str(self.root / 'output')])
        self.assertFalse((self.root / 'output').exists())

    def header_seed(self, target):
        root = self.root / ('headers-' + target)
        include = root / 'usr/include'
        for directory in ('sys', target):
            (include / directory).mkdir(parents=True)
        for name in ('stddef.h', 'stdio.h', 'sys/types.h', 'sys/cdefs.h', 'sys/common_ansi.h', target + '/ansi.h'):
            (include / name).write_text('source header fixture\n')
        (include / 'machine').symlink_to(target)
        if target == 'aarch64':
            (include / 'arm').mkdir()
            (include / 'arm/ansi.h').write_text('arm ABI header fixture\n')
        return root

    def test_bootstrap_headers_require_source_and_contained_target_inventory(self):
        spec_ = importlib.util.spec_from_file_location('bootstrap_libgcc', PROFILE / 'cross/bootstrap_libgcc.py')
        support = importlib.util.module_from_spec(spec_)
        spec_.loader.exec_module(support)
        root = self.header_seed('aarch64')
        record = support.headers(root, 'aarch64')
        self.assertEqual(record['source_commit'], 'a' * 40)
        self.assertEqual(record['root'], str(root))
        self.assertIn('usr/include/machine', record['inventory'])
        with patch.dict(os.environ, {'EMBERBSD_SYSROOT_SOURCE': ''}):
            self.assertRaisesRegex(SDKError, 'source commit', support.headers, root, 'aarch64')
        provenance = self.root / 'headers-provenance.json'
        provenance.write_text('{"source": "fixture"}\n')
        with patch.dict(os.environ, {'EMBERBSD_SYSROOT_PROVENANCE': str(provenance)}):
            claimed = support.headers(root, 'aarch64')
            self.assertEqual(claimed['provenance']['sha256'], inventory.sha256_file(provenance))
        (root / 'usr/include/stddef.h').write_text('changed source header\n')
        self.assertNotEqual(support.headers(root, 'aarch64'), record)
        self.assertRaises(SDKError, support.headers, root, 'amd64')
        (root / 'usr/include/machine').unlink()
        (root / 'usr/include/machine').symlink_to(self.seed / 'usr/include')
        self.assertRaises(SDKError, support.headers, root, 'aarch64')

    def test_bootstrap_libgcc_checks_installed_target_support(self):
        spec_ = importlib.util.spec_from_file_location('bootstrap_libgcc', PROFILE / 'cross/bootstrap_libgcc.py')
        support = importlib.util.module_from_spec(spec_)
        spec_.loader.exec_module(support)
        work = self.root / 'bootstrap-cross'
        prefix = work / 'toolchain'
        triplet = 'aarch64--netbsd'
        crt = prefix / 'lib/gcc' / triplet / host.VERSION
        crt.mkdir(parents=True)
        frontend = work / 'build/gcc/Makefile'
        frontend.parent.mkdir(parents=True)
        frontend.write_text('inhibit_libc = true\n')
        library = work / 'build' / triplet / 'libgcc/Makefile'
        library.parent.mkdir(parents=True)
        library.write_text('enable_shared = no\n')
        (work / 'inputs.txt').write_text('mode=kernel\nbootstrap_libgcc=yes\n')
        headers = self.header_seed('aarch64')
        jsonio.write_json(work / 'bootstrap-headers.json', support.headers(headers, 'aarch64'))
        object_ = b'\x7fELF\x02\x01\x01'.ljust(16, b'\0') + struct.pack('<HHIQQQIHHHHHH', 1, 183, 1, 0, 0, 0, 0, 64, 0, 0, 0, 0, 0)
        member = b'probe.o/'.ljust(16) + b'0'.ljust(12) + b'0'.ljust(6) + b'0'.ljust(6) + b'100644'.ljust(8) + str(len(object_)).encode().ljust(10) + b'`\n' + object_
        archive = crt / 'libgcc.a'
        archive.write_bytes(b'!<arch>\n' + member)
        for name in ('crtbegin.o', 'crtbeginS.o', 'crtend.o', 'crtendS.o'):
            (crt / name).write_bytes(object_)
        commands = []
        def logged(argv, log, env, cwd, **kwargs):
            self.assertEqual(kwargs.get('quarantine'), work)
            self.assertEqual(cwd, work / 'build')
            commands.append([str(value) for value in argv])
        def capture(argv, **kwargs):
            self.assertEqual(str(argv[0]), str(prefix / 'bin' / (triplet + '-gcc')))
            if argv[1] == '-print-sysroot':
                return str(headers) + '\n'
            return str(crt / str(argv[1]).removeprefix('-print-file-name=')) + '\n'
        configured = ('Configured with: /source/configure --without-headers --disable-shared --disable-threads --with-sysroot=' + str(headers) + '\n').encode()
        banner = SimpleNamespace(stdout=b'', stderr=configured + b'Thread model: single\n')
        with patch.object(support, 'logged', side_effect=logged), patch.object(support, 'capture', side_effect=capture), patch.object(support, 'target_tools', return_value={'AR_FOR_TARGET': 'audited-ar'}), patch.object(support.process, 'capture', return_value=banner):
            support.build(work, prefix, 'aarch64', self.make, '2', {})
            self.assertEqual([command[-1] for command in commands], ['all-target-libgcc', 'install-target-libgcc'])
            record = jsonio.read_json(work / 'bootstrap-libgcc.json')
            self.assertEqual(record['scope'], 'static-libgcc-bootstrap-only')
            self.assertEqual(record['archive']['elf_members'], 1)
            self.assertEqual(record['target'], 'aarch64')
            self.assertEqual(record['bootstrap_headers_sha256'], inventory.sha256_file(work / 'bootstrap-headers.json'))
            self.assertFalse((work / 'build-success').exists())
            self.assertEqual(len(record['files']), 5)
            (work / 'bootstrap-libgcc.json').unlink()
            archive.write_bytes(b'!<arch>\n')
            self.assertRaisesRegex(SDKError, 'empty', support.build, work, prefix, 'aarch64', self.make, '2', {})
            self.assertFalse((work / 'bootstrap-libgcc.json').exists())
            archive.write_bytes(b'!<arch>\n' + member)
            (crt / 'crtbeginS.o').write_bytes(object_[:18] + struct.pack('<H', 62) + object_[20:])
            self.assertRaises(SDKError, support.build, work, prefix, 'aarch64', self.make, '2', {})
            (crt / 'crtbeginS.o').write_bytes(object_)
            library.write_text('enable_shared = yes\n')
            self.assertRaisesRegex(SDKError, 'shared', support.build, work, prefix, 'aarch64', self.make, '2', {})
            library.write_text('enable_shared = no\n')
            (crt / 'libgcc_s.so.1').write_bytes(object_)
            self.assertRaisesRegex(SDKError, 'Shared libgcc', support.build, work, prefix, 'aarch64', self.make, '2', {})
            (crt / 'libgcc_s.so.1').unlink()
            with patch.object(support, 'capture', return_value='/wrong/bootstrap/libgcc.a\n'):
                self.assertRaises(SDKError, support.build, work, prefix, 'aarch64', self.make, '2', {})
            banner.stderr = configured + b'Thread model: posix\n'
            count = len(commands)
            self.assertRaisesRegex(SDKError, 'single-thread', support.build, work, prefix, 'aarch64', self.make, '2', {})
            self.assertEqual(len(commands), count)
            banner.stderr = b'Thread model: single\n'
            self.assertRaisesRegex(SDKError, 'nonshared', support.build, work, prefix, 'aarch64', self.make, '2', {})
            self.assertEqual(len(commands), count)
            banner.stderr = configured + b'Thread model: single\n'
            frontend.write_text('inhibit_libc = false\n')
            count = len(commands)
            self.assertRaisesRegex(SDKError, 'inhibit_libc', support.build, work, prefix, 'aarch64', self.make, '2', {})
            self.assertEqual(len(commands), count)
            frontend.write_text('inhibit_libc = true\n')
            (headers / 'usr/include/stddef.h').write_text('changed after compiler configuration\n')
            self.assertRaisesRegex(SDKError, 'headers changed', support.build, work, prefix, 'aarch64', self.make, '2', {})
            self.assertEqual(len(commands), count)
            (headers / 'usr/include/stddef.h').write_text('source header fixture\n')
            def changed_header(argv, log, env, cwd, **kwargs):
                logged(argv, log, env, cwd, **kwargs)
                if argv[-1] == 'install-target-libgcc':
                    (headers / 'usr/include/stddef.h').write_text('changed during support build\n')
            with patch.object(support, 'logged', side_effect=changed_header):
                self.assertRaisesRegex(SDKError, 'headers changed during', support.build, work, prefix, 'aarch64', self.make, '2', {})
            self.assertFalse((work / 'bootstrap-libgcc.json').exists())
            (headers / 'usr/include/stddef.h').write_text('source header fixture\n')
            def changed_record(argv, log, env, cwd, **kwargs):
                logged(argv, log, env, cwd, **kwargs)
                if argv[-1] == 'install-target-libgcc':
                    with (work / 'bootstrap-headers.json').open('a') as stream:
                        stream.write('\n')
            with patch.object(support, 'logged', side_effect=changed_record):
                self.assertRaisesRegex(SDKError, 'header input record changed', support.build, work, prefix, 'aarch64', self.make, '2', {})
            self.assertFalse((work / 'bootstrap-libgcc.json').exists())

    def test_patch_literal_plus_unsafe_hash_and_abi(self):
        patch_=self.recipe/'patches/patch-libstdc++-v3_configure_math'
        patch_.write_text('$NetBSD: provenance$\nnormalized patch data\n')
        self.distinfo()
        self.assertIn(patch_.name,host.audit_source(self.pkgsrc,self.archive)[1])
        patch_.write_text('mutated')
        self.assertRaises(SDKError,host.audit_source,self.pkgsrc,self.archive)
        patch_.unlink();self.distinfo()
        info=self.recipe/'distinfo';original=info.read_text();info.write_text(original+'SHA1 (patch-unsafe/name) = '+'a'*40+'\n')
        self.assertRaises(SDKError,host.audit_source,self.pkgsrc,self.archive)
        info.write_text(original)
        (self.recipe/'Makefile').write_text('--disable-libssp libtool_VERSION=9:')
        self.assertRaises(SDKError,host.audit_source,self.pkgsrc,self.archive)

    def test_real_tar_patch_and_abi_selection(self):
        source=self.root/'source';(source/'libstdc++-v3').mkdir(parents=True)
        (source/'fixture').write_text('before\n')
        configure=source/'libstdc++-v3/configure';configure.write_text('libtool_VERSION=6:36:0\n');configure.chmod(0o755)
        self.source_patch.write_text('--- fixture.orig\n+++ fixture\n@@ -1 +1 @@\n-before\n+after\n')
        self.distinfo()
        with tarfile.open(self.archive,'w') as archive:archive.add(source,arcname='gcc-16.2.0')
        with patch.object(host,'source_row',return_value=['gcc','16.2.0','fixture',inventory.sha256_file(self.archive)]):
            output=self.root/'prepared'
            previous_mask = os.umask(0o077)
            try:
                host.prepare_source(self.pkgsrc,self.archive,output)
            finally:
                os.umask(previous_mask)
            self.assertEqual((output/'fixture').read_text(),'after\n')
            self.assertEqual((output/'libstdc++-v3/configure').read_text(),'libtool_VERSION=7:36:0\n')
            self.assertEqual((output/'libstdc++-v3/configure').stat().st_mode&0o777,0o755)
            self.assertRaises(SDKError,host.prepare_source,self.pkgsrc,self.archive,output)

    def test_resume_stage_preservation_and_frontend_guard(self):
        work=self.root/'resume';(work/'build/gcc').mkdir(parents=True);(work/'stage/empty').mkdir(parents=True)
        triplet='x86_64--netbsd'
        (work/'build'/triplet/'libgcc').mkdir(parents=True)
        for name in ('Makefile','config.cache','config.status','config.log','auto-host.h','configargs.h','xgcc','cc1','cc1plus'):(work/'build/gcc'/name).write_text('frontend '+name)
        (work/'build'/triplet/'libgcc/Makefile').write_text('metadata')
        (work/'build'/triplet/'libgcc/value.o').write_text('preserved target object')
        (work/'stage/file').write_text('partial stage')
        (work/'stage/link').symlink_to('file')
        (work/'inputs.txt').write_text('scope=runtime-only-bootstrap\n')
        original=inventory.snapshot_tree(work/'stage')
        state=SimpleNamespace(work=work,resume='runtime',triplet=triplet,selection='libgcc,libstdc++')
        backup=backup_resume(state)
        self.assertEqual(inventory.snapshot_tree(backup/'stage'),original)
        self.assertEqual(inventory.snapshot_tree(work/'stage'),{})
        self.assertFalse((work/'build'/triplet/'libgcc/Makefile').exists())
        self.assertEqual((work/'build'/triplet/'libgcc/value.o').read_text(),'preserved target object')
        verify_frontend(backup)
        (work/'build/gcc/cc1').write_text('mutated frontend')
        self.assertRaises(SDKError,verify_frontend,backup)

    def test_completed_extension_and_mutations(self):
        work=self.root/'completed';(work/'stage').mkdir(parents=True)
        (work/'stage/recorded').write_text('complete')
        (work/'stage/second').write_text('another legacy manifest row')
        (work/'build-success').write_text('runtime-only-bootstrap\n')
        (work/'inputs.txt').write_text('runtime_libraries=libgcc,libstdc++\n')
        host.manifests(work/'stage',work)
        # Independent legacy receipt orders entire digest rows, not file names.
        expected = ''.join(sorted(inventory.sha256_file(path) + '  ./' + path.name + '\n' for path in (work/'stage').iterdir()))
        self.assertEqual((work/'stage.sha256').read_text(), expected)
        verify_completed_stage(work)
        self.assertTrue(check_prior(work,selected(True,True)[0],'runtime'))
        self.assertRaises(SDKError,check_prior,work,selected(True)[0],'yes')
        (work/'stage/additional').write_text('unrecorded')
        self.assertRaises(SDKError,verify_completed_stage,work)
        (work/'inputs.txt').write_text('runtime_libraries=libgcc,libstdc++,libgomp\n')
        self.assertRaises(SDKError,check_prior,work,selected()[0],'runtime')

    def test_support_checkpoint_and_every_parent_mutation(self):
        work=self.root/'support'
        for name in ('src','build/gcc','stage'):(work/name).mkdir(parents=True)
        (work/'src/source').write_text('source bytes')
        (work/'build/gcc/object.o').write_text('native object')
        fields={'scope':'runtime-only-external-compiler','triplet':'x86_64--netbsd','sysroot':str(self.seed)}
        files=[PROFILE/'bootstrap/pipeline.py',PROFILE/'bootstrap/support_resume.py']
        (work/'inputs.txt').write_text(''.join(key+'='+value+'\n' for key,value in fields.items())+host.digest_rows(files))
        for name in ('external-compiler.txt','support-build.log','support-host.log','configure.log','patch.log'):(work/name).write_text('actual failure fixture')
        failure=self.root/'failure';failure.write_text('2\n')
        support('checkpoint',work,failure)
        support('check',work)
        for path in (work/'src/source',work/'build/gcc/object.o',work/'support-parent/failure-exit.txt',work/'support-parent/helpers/pipeline.py'):
            original=path.read_bytes();path.write_bytes(original+b'changed')
            self.assertRaises(SDKError,support,'check',work)
            path.write_bytes(original)
        support('resume',work)
        self.assertIn('historical_helper_map=',(work/'inputs.txt').read_text())
        self.assertEqual(field((work/'inputs.txt').read_text(),'scope'),'runtime-only-external-support-resume')

    def test_application_receipt_guard(self):
        builder=LibstdcxxRebuild(['--check','amd64',str(self.pkgsrc),str(self.pkgsrc),str(self.archive),str(self.kernel),str(self.seed),str(self.root/'old'),str(self.root/'new')])
        receipt=self.kernel.parent/'inputs.txt'
        hashes=host.digest_rows([self.archive,self.recipe/'distinfo'])
        good='mode=applications\ntriplet=x86_64--netbsd\ntriplet=x86_64--netbsd\n'+hashes
        receipt.write_text(good);builder.compiler_receipt()
        for value in ('mode=kernel\ntriplet=x86_64--netbsd\n'+hashes,good+'mode=applications\n',good+'triplet=aarch64--netbsd\n','mode=applications\ntriplet=x86_64--netbsd\n'):
            receipt.write_text(value)
            self.assertRaises(SDKError,builder.compiler_receipt)

    def test_missing_sdk_duplicate_source_and_api(self):
        self.assertRaises(RuntimeError,sdk_source.arguments,['--sdk-source',sdk_source.load(),'--sdk-source',sdk_source.load()])
        self.assertRaises(RuntimeError,sdk_source.load,str(self.root))

    def test_external_dispatch_native_tools_and_no_frontend(self):
        work=self.root/'external'
        for name in ('src/libgcc','src/libstdc++-v3','build/gcc','stage'):(work/name).mkdir(parents=True)
        native=self.root/'native';native.mkdir()
        object_=self.root/'native.o';object_.write_text('native-object')
        self.executable(native/'tool','test "$(cat "$1")" = native-object\n')
        target=self.root/'target';target.mkdir()
        self.executable(target/'nm',"echo 'Target nm cannot inspect a native object' >&2\nexit 96\n")
        make=self.root/'dispatch-make'
        log=self.root/'dispatch.log'
        self.executable(make,'''configure=no
support_cpp=no
for argument; do
 case "$argument" in
  all-gcc|all-target-*|install-gcc|install-target-*|libgcc-support) exit 99;;
  configure-gcc) configure=yes;;
  all-build-libcpp) support_cpp=yes;;
 esac
done
if [ "$configure" = yes ]; then
 test "$support_cpp" = yes
 "$NM" "OBJECT"
 "$AR" "OBJECT"
 "$RANLIB" "OBJECT"
fi
case "$PWD" in */libgcc|*/libstdc++-v3)
 test "$NM" = "$NM_FOR_TARGET"
 test "$AR" = "$AR_FOR_TARGET"
 test "$RANLIB" = "$RANLIB_FOR_TARGET";;
esac
printf '%s\n' "$*" >> 'LOG'
'''.replace('OBJECT',str(object_)).replace('LOG',str(log)))
        self.executable(work/'src/config.guess','echo aarch64-apple-darwin\n')
        configure='test "$NM" = "$NM_FOR_TARGET"\ntest "$AR" = "$AR_FOR_TARGET"\nprintf "CC = %s\\n" "$CC" > Makefile\n'
        for name in ('libgcc','libstdc++-v3'):self.executable(work/'src'/name/'configure',configure)
        env={name.upper()+'_FOR_TARGET':str(target/('aarch64--netbsd-'+name)) for name in host.TOOLS}
        env.update(PATH=str(target)+':'+os.environ['PATH'],AR=str(native/'tool'),NM=str(native/'tool'),RANLIB=str(native/'tool'))
        state=SimpleNamespace(work=work,make=make,count='2',env=env,triplet='aarch64--netbsd',target_flags='-O2',sysroot=self.seed,tools={'gcc':self.kernel/'bin/x86_64--netbsd-gcc'})
        state.run_logged = lambda argv, log_, env_=None, cwd=None: host.logged(argv, log_, env_, cwd, quarantine=work)
        build_external(state)
        command_lines=log.read_text().splitlines()
        self.assertTrue(any('all-build-libcpp' in line and 'configure-gcc' in line for line in command_lines))
        self.assertTrue(any('libgcc.mvars tconfig.h machmode.h mode-classes.def version.h' in line for line in command_lines))
        self.assertEqual(sum(line=='-j2 all' for line in command_lines),2)
        self.assertTrue((work/'build/gcc/include').is_dir())
        self.assertIn('target_objects=external-compiler',(work/'external-runtime-plan.txt').read_text())
        (work/'build/gcc/cc1').write_text('unexpected frontend')
        self.assertRaises(SDKError,build_external,state)
        (work/'build/gcc/cc1').unlink()
        env['NM']=str(target/'nm')
        self.assertRaises(SDKError,build_external,state)

    def test_cross_configure_both_modes_and_bootstrap_make(self):
        spec_=importlib.util.spec_from_file_location('cross_pipeline',PROFILE/'cross/pipeline.py')
        cross=importlib.util.module_from_spec(spec_);spec_.loader.exec_module(cross)
        source=self.root/'cross-source';source.mkdir()
        (source/'fixture').write_text('before\n')
        config=self.root/'configure.json'
        self.executable(source/'configure',"printf '%s\\n' \"$@\" > 'CONFIG'\nprintf '%s\\n' \"CPPFLAGS=$CPPFLAGS\" \"CFLAGS=$CFLAGS\" \"CXXFLAGS=$CXXFLAGS\" \"LDFLAGS=$LDFLAGS\" \"inhibit_libc=${inhibit_libc-}\" > 'CONFIG.flags'\nexit 97\n".replace('CONFIG',str(config)))
        self.source_patch.write_text('--- fixture.orig\n+++ fixture\n@@ -1 +1 @@\n-before\n+after\n');self.distinfo()
        with tarfile.open(self.archive,'w') as archive:archive.add(source,arcname='gcc-16.2.0')
        row=['gcc','16.2.0','fixture',inventory.sha256_file(self.archive)]
        host_cc=self.root/'host-cc'
        self.executable(host_cc,'''case "$1" in
 --version) echo 'fixture GCC16'; exit 0;;
 -dumpmachine) echo fixture-host; exit 0;;
esac
while [ "$#" -gt 0 ]; do
 if [ "$1" = -o ]; then printf '#!/bin/sh\nexit 0\n' > "$2"; chmod +x "$2"; exit 0; fi
 shift
done
exit 1
''')
        tools=self.root/'os-tools';(tools/'bin').mkdir(parents=True)
        self.executable(tools/'bin/nbgmake',"echo 'fixture GNU make'\n")
        observed=[]
        def binutils(args,make_override=None):
            target=args[1];work=Path(args[2]);triplet=host.TARGETS[target][0]
            self.assertEqual(make_override,tools/'bin/nbgmake')
            observed.append((target,str(work)))
            (work/'prefix/bin').mkdir(parents=True)
            (work/'prefix'/triplet/'lib/ldscripts').mkdir(parents=True)
            for name in host.BINUTILS:self.executable(work/'prefix/bin'/(triplet+'-'+name),"echo 'fixture GNU tool2.47'\n")
            (work/'prefix'/triplet/'lib/ldscripts/elf.x').write_text('linker script fixture')
            (work/'inputs.txt').write_text('target='+target+'\ntriplet='+triplet+'\n')
        with patch.object(host,'source_row',return_value=row),patch.object(cross,'host_compilers',return_value=(str(host_cc),str(host_cc))),patch.object(cross,'binutils_main',side_effect=binutils),patch.dict(os.environ,{'HOST_CPPFLAGS':'-isysroot /fixture/sdk','HOST_LDFLAGS':'-isysroot /fixture/link-sdk'}):
            for target in host.TARGETS:
                triplet=host.TARGETS[target][0]
                headers = self.header_seed(target)
                runtime=self.seed/'usr/pkg/gcc16'
                (runtime/'lib/gcc'/triplet/'16.2.0').mkdir(parents=True)
                (runtime/'lib/gcc'/triplet/'16.2.0/crtbegin.o').write_text('crt fixture')
                (runtime/'include/c++'/triplet).mkdir(parents=True)
                for mode in ('applications','kernel','kernel-bootstrap'):
                    output=self.root/(target+'-'+mode)
                    args=['--target',target]+(['--kernel'] if mode!='applications' else [])+(['--bootstrap-libgcc'] if mode=='kernel-bootstrap' else [])+[str(self.pkgsrc),str(self.archive)]+([str(self.seed)] if mode=='applications' else ([str(headers)] if mode=='kernel-bootstrap' else []))+[str(tools),str(self.math),str(output)]
                    with self.assertRaises(SDKError) as raised:cross.build_main(args)
                    self.assertEqual(getattr(raised.exception,'returncode',None),97)
                    arguments=config.read_text().splitlines()
                    self.assertIn('--target='+triplet,arguments)
                    self.assertIn('--with-as='+str(output/'toolchain/bin'/(triplet+'-as')),arguments)
                    self.assertIn('--with-ld='+str(output/'toolchain/bin'/(triplet+'-ld')),arguments)
                    self.assertEqual('--without-headers' in arguments,mode!='applications')
                    self.assertEqual('--disable-threads' in arguments,mode!='applications')
                    self.assertEqual('--with-sysroot='+str(self.seed) in arguments,mode=='applications')
                    self.assertEqual('--with-sysroot='+str(headers) in arguments,mode=='kernel-bootstrap')
                    self.assertEqual((Path(str(config)+'.flags')).read_text().splitlines(),['CPPFLAGS=-isysroot /fixture/sdk','CFLAGS=-O2 -isysroot /fixture/sdk','CXXFLAGS=-O2 -isysroot /fixture/sdk','LDFLAGS=-isysroot /fixture/link-sdk','inhibit_libc=' + ('true' if mode=='kernel-bootstrap' else '')])
                    self.assertEqual(os.readlink(output/'toolchain'/triplet/'bin/objcopy'),'../../bin/'+triplet+'-objcopy')
                    self.assertEqual((output/'src/fixture').read_text(),'after\n')
                    self.assertEqual('bootstrap_libgcc=yes\n' in (output/'inputs.txt').read_text(),mode=='kernel-bootstrap')
            self.assertEqual(len(observed),6)
            # Complete the dispatch fixture. A bootstrap receipt must hash the
            # final inputs after the AArch64 installed-compiler probe appends.
            source.joinpath('configure').write_text(source.joinpath('configure').read_text().replace('exit 97\n', ''))
            with tarfile.open(self.archive,'w') as archive:archive.add(source,arcname='gcc-16.2.0')
            row[3] = inventory.sha256_file(self.archive)
            events = []
            real_spec = importlib.util.spec_from_file_location('real_compiler_probes', PROFILE / 'cross/tests/compiler_probes.py')
            real_probes = importlib.util.module_from_spec(real_spec)
            real_spec.loader.exec_module(real_probes)
            def compile_split(argv, log, env):
                Path(argv[-1]).with_suffix('.dwo').write_bytes(b'split DWARF fixture')
            def inspect_split(argv, env):
                return 'split_record\n' if argv[1] == '--debug-dump=str-offsets' else 'DW_UT_skeleton DW_UT_split_compile\n'
            def split(args):
                events.append('split-dwarf')
                # Keep the real CLI parser and workspace setup at this boundary.
                # Only target compilation and ELF inspection use fixtures.
                with patch.object(real_probes, 'logged', side_effect=compile_split), patch.object(real_probes, 'capture', side_effect=inspect_split):
                    real_probes.split_dwarf(args)
            class Probes:
                def create_module(self, spec):
                    return None
                def exec_module(self, module):
                    module.split_dwarf = split
                    def lto(args):
                        events.append('lto')
                        args[1].mkdir()
                        (args[1] / 'inputs.txt').write_text('installed-lto-probe=passed\n')
                    module.lto_binutils = lto
            def static_support(work, prefix, target, make, count, env):
                self.assertIn('installed-lto-probe=passed\n', (work / 'inputs.txt').read_text())
                events.append(('bootstrap', inventory.sha256_file(work / 'inputs.txt')))
            probe_spec = importlib.machinery.ModuleSpec('gcc16_compiler_probes', Probes())
            with patch.object(cross, 'check_compilers'), patch.object(cross, 'build_bootstrap_libgcc', side_effect=static_support), patch.object(importlib.util, 'spec_from_file_location', return_value=probe_spec):
                for mode in ('applications', 'kernel', 'kernel-bootstrap'):
                    events.clear()
                    output = self.root / ('complete-' + mode)
                    args = (['--kernel'] if mode != 'applications' else []) + (['--bootstrap-libgcc'] if mode == 'kernel-bootstrap' else [])
                    args += [str(self.pkgsrc), str(self.archive)] + ([str(self.seed)] if mode == 'applications' else ([str(self.root / 'headers-aarch64')] if mode == 'kernel-bootstrap' else [])) + [str(tools), str(self.math), str(output)]
                    cross.build_main(args)
                    self.assertIn('split_record', (output / 'split-dwarf/test.c').read_text())
                    self.assertIn('DW_UT_skeleton', (output / 'split-dwarf/info.txt').read_text())
                    self.assertEqual(events[:2], ['split-dwarf', 'lto'])
                    self.assertEqual(len(events), 3 if mode == 'kernel-bootstrap' else 2)
                    if mode == 'kernel-bootstrap':
                        self.assertEqual(events[2], ('bootstrap', inventory.sha256_file(output / 'inputs.txt')))

    @unittest.skipUnless(os.name == 'posix', 'Owned producer groups require POSIX')
    def test_actual_cli_term_and_hup_drain_descendants(self):
        import json
        import signal
        import subprocess
        import time
        projection=self.root/'cli-profile'
        for name in ('host.py','bootstrap/prepare-source.py','runtime/recipe/files/sdk_source.py'):
            target=projection/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PROFILE/name,target)
        (projection/'sources.tsv').write_text('gcc\t16.2.0\tfixture\t'+self.expected+'\n')
        for number in (signal.SIGTERM,signal.SIGHUP):
            with self.subTest(signal=number):
                area=self.root/('signal-'+str(number));area.mkdir()
                ready=area/'ready.json';child_ready=area/'child-ready'
                bin_=area/'bin';bin_.mkdir()
                child_code="import os,signal,time;from pathlib import Path;os.setpgid(0,0);signal.signal(signal.SIGTERM,signal.SIG_IGN);Path("+repr(str(child_ready))+").write_text(str(os.getpid()));time.sleep(60)"
                fake='#!'+sys.executable+'\nimport json,os,subprocess,sys,time\nfrom pathlib import Path\n'
                fake+='child=subprocess.Popen([sys.executable,"-c",'+repr(child_code)+'])\n'
                fake+='while not Path('+repr(str(child_ready))+').exists():time.sleep(0.01)\n'
                fake+='Path('+repr(str(ready))+').write_text(json.dumps({"parent":os.getpid(),"child":child.pid,"group":os.getpgrp(),"session":os.getsid(0)}))\ntime.sleep(60)\n'
                (bin_/'tar').write_text(fake);(bin_/'tar').chmod(0o755)
                env=dict(os.environ,PATH=str(bin_)+':'+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
                command=[sys.executable,'-I','-S','-B',str(projection/'bootstrap/prepare-source.py'),str(self.pkgsrc),str(self.archive),str(area/'source'),'--sdk-source',sdk_source.load()]
                with (area/'cli.log').open('wb') as log:
                    cli=subprocess.Popen(command,env=env,stdout=log,stderr=log,start_new_session=True)
                    identity=None
                    try:
                        deadline=time.monotonic()+10
                        while not ready.exists() and cli.poll() is None and time.monotonic()<deadline:time.sleep(0.02)
                        self.assertTrue(ready.exists(),(area/'cli.log').read_text())
                        identity=json.loads(ready.read_text())
                        self.assertNotEqual(identity['group'],cli.pid,'The mutating producer needs its own group')
                        self.assertEqual(os.getsid(identity['child']),identity['session'])
                        self.assertNotEqual(os.getpgid(identity['child']),identity['group'])
                        cli.send_signal(number)
                        self.assertEqual(cli.wait(timeout=15),128+number)
                        with self.assertRaises(ProcessLookupError):os.killpg(identity['group'],0)
                        for pid in (identity['parent'],identity['child']):
                            with self.assertRaises(ProcessLookupError):os.kill(pid,0)
                    finally:
                        if cli.poll() is None:
                            cli.send_signal(signal.SIGINT)
                            try:cli.wait(timeout=15)
                            except subprocess.TimeoutExpired:
                                os.killpg(cli.pid,signal.SIGKILL);cli.wait()
                        if identity is not None:
                            for pid in (identity['parent'],identity['child']):
                                try:
                                    if os.getsid(pid)==identity['session']:os.killpg(os.getpgid(pid),signal.SIGKILL)
                                except ProcessLookupError:pass


if __name__=='__main__':
    sdk_source.install_signal_handlers()
    unittest.main(argv=[sys.argv[0]]+ARGS)
