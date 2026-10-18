# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; audited cross-built GCC16 target runtime orchestration.
import json
import os
from pathlib import Path
import platform
import re
import shutil
from emberbsd_sdk import elf, inventory, paths
from host import *
import sdk_source
from runtime_libraries import selected
from resume_state import check_resume, backup_resume, verify_frontend
from external_compiler import compiler_state, check_support_resume, build_external

HERE = PROFILE / 'bootstrap'


class Bootstrap:
    def __init__(self, args):
        args = list(args)
        self.check, self.external, self.gomp, self.atomic = False, False, False, False
        self.resume = 'no'
        flags = {'--check': 'check', '--external-compiler': 'external', '--with-libgomp': 'gomp', '--with-libatomic': 'atomic'}
        while args and args[0] != '--target':
            flag = args.pop(0)
            if flag in flags:
                name = flags[flag]
                require(not getattr(self, name), 'Duplicate option: ' + flag)
                setattr(self, name, True)
            elif flag in ('--resume', '--resume-runtime', '--resume-support'):
                require(self.resume == 'no', 'Duplicate resume mode')
                self.resume = {'--resume': 'yes', '--resume-runtime': 'runtime', '--resume-support': 'support'}[flag]
            else:
                require(False, 'Unknown build option: ' + flag)
        require(len(args) == 8 and args[0] == '--target', 'Usage: build.py [--check] [--external-compiler] [--resume|--resume-runtime|--resume-support] [--with-libgomp] [--with-libatomic] --target TARGET PKGSRC ARCHIVE COMPILER SYSROOT MATH WORK --sdk-source SOURCE')
        self.target = args[1]
        require(self.target in TARGETS, 'Unsupported target')
        self.triplet, self.machine, self.arch, self.target_flags = TARGETS[self.target]
        self.pkgsrc, self.archive, self.kernel, self.sysroot, self.math, self.work = [build_path(value) for value in args[2:]]
        require(self.resume != 'support' or self.external, '--resume-support requires --external-compiler')
        if self.resume == 'no':
            new_path(self.work)
        else:
            paths.real_directory(self.work)
            assert_recoverable(self.work)
        self.sysroot = Path(paths.canonical_existing(self.sysroot))
        if self.external:
            self.kernel = Path(paths.canonical_existing(self.kernel))
        self.count = jobs(4)
        self.origin = os.environ.get('EMBERBSD_SYSROOT_SOURCE', '')
        require(re.fullmatch(r'[0-9a-f]{40}', self.origin), 'Set EMBERBSD_SYSROOT_SOURCE to verified full EmberBSD source commit')
        provenance = os.environ.get('EMBERBSD_SYSROOT_PROVENANCE')
        self.provenance = build_path(provenance) if provenance else None
        if self.provenance:
            paths.regular_file(self.provenance)
        self.scope = 'runtime-only-external-support-resume' if self.resume == 'support' else ('runtime-only-external-compiler' if self.external else 'runtime-only-bootstrap')
        self.selection, self.sonames = selected(self.gomp, self.atomic)

    def host_fields(self):
        return {'host_cc': os.environ.get('HOST_CC', 'cc'), 'host_cxx': os.environ.get('HOST_CXX', 'c++'), 'host_cflags': os.environ.get('HOST_CFLAGS', '-O2'), 'host_cxxflags': os.environ.get('HOST_CXXFLAGS', '-O2'), 'host_ar': os.environ.get('AR', 'auto'), 'host_nm': os.environ.get('NM', 'auto'), 'host_ranlib': os.environ.get('RANLIB', 'auto')}

    def compiler_version(self, executable):
        result = process.capture([str(executable), '-v'], env=environment())
        return (result.stdout + result.stderr).decode()

    def check_elf(self, path, root):
        resolved = Path(path).resolve(strict=True)
        require(paths.inside(resolved, root), 'Target ELF escapes supplied tree')
        require(elf.read_elf_header(resolved, machine=self.machine) is not None, 'Target ELF missing or architecture mismatch')

    def preflight(self):
        self.tools = check_compilers(self.kernel, self.target)
        for name in ('stddef.h', 'stdio.h', 'pthread.h', 'math.h'):
            header = (self.sysroot / 'usr/include' / name).resolve(strict=True)
            require(paths.inside(header, self.sysroot), 'Target header escapes supplied sysroot')
            paths.regular_file(header)
        for name in ('libc.so.12', 'libpthread.so.1', 'libm.so.0', 'crt0.o'):
            self.check_elf(self.sysroot / 'usr/lib' / name, self.sysroot)
        self.math = check_math(self.math)
        expected, _ = audit_source(self.pkgsrc, self.archive)
        self.kernel_receipt = self.kernel.parent / 'inputs.txt'
        if self.external:
            self.external_state = compiler_state(self)
        else:
            receipt = self.kernel_receipt.read_text()
            require('mode=kernel\n' in receipt, 'Missing audited kernel compiler inputs.txt receipt')
            for digest in (expected, sha(self.pkgsrc / 'lang/gcc16/distinfo')):
                require(re.search('^' + digest + r'\s', receipt, re.M), 'Kernel compiler source or patch receipt mismatch')
        self.make = os.environ.get('GNU_MAKE') or shutil.which('gmake') or shutil.which('make')
        require(self.make and Path(self.make).is_absolute() and os.access(self.make, os.X_OK), 'GNU_MAKE must be absolute executable')
        require(capture([self.make, '--version']).startswith('GNU Make '), 'GNU make required')
        self.env = target_tools(self.kernel, self.target)
        fields = self.host_fields()
        self.env.update(CACHE)
        self.env.update(CC=fields['host_cc'], CXX=fields['host_cxx'], CFLAGS=fields['host_cflags'], CXXFLAGS=fields['host_cxxflags'], CFLAGS_FOR_TARGET=self.target_flags, CXXFLAGS_FOR_TARGET=self.target_flags, LDFLAGS_FOR_TARGET='-Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-z,relro')
        for key, field_ in [('AR', 'host_ar'), ('NM', 'host_nm'), ('RANLIB', 'host_ranlib')]:
            if fields[field_] != 'auto':
                self.env[key] = fields[field_]
        if self.resume == 'support':
            check_support_resume(self)
        elif self.resume != 'no':
            check_resume(self)
        print('target=' + self.target + '\ntriplet=' + self.triplet + '\nabi=libstdc++.so.7\ntarget_flags=' + self.target_flags + '\nseed_source=' + self.origin + '\nruntime_prefix=/usr/pkg/gcc16\nstage=' + str(self.work / 'stage') + '\nresume=' + self.resume + '\ntoolexeclibdir=/usr/pkg/gcc16/lib\nruntime_libraries=' + self.selection + '\nar_for_target=' + self.env['AR_FOR_TARGET'] + '\nnm_for_target=' + self.env['NM_FOR_TARGET'])
        if self.external:
            print('compiler_mode=external-posix\nsupport_target=gcc-leaf-metadata-v1')

    def configure_args(self):
        args = ['--target=' + self.triplet, '--prefix=/usr/pkg/gcc16', '--libdir=/usr/pkg/gcc16/lib', '--with-toolexeclibdir=/usr/pkg/gcc16/lib', '--with-local-prefix=/usr/pkg/gcc16', '--with-gxx-include-dir=/usr/pkg/gcc16/include/c++', '--with-sysroot=' + str(self.sysroot), '--with-native-system-header-dir=/usr/include']
        args += ['--with-' + name + '=' + str(self.math) for name in ('gmp', 'mpfr', 'mpc')]
        args += ['--with-gnu-as', '--with-gnu-ld', '--with-as=' + str(self.tools['as']), '--with-ld=' + str(self.tools['ld']), '--enable-languages=c,c++', '--disable-bootstrap', '--disable-multilib', '--enable-shared', '--enable-threads=posix', '--enable-long-long', '--disable-libssp', '--disable-libstdcxx-pch', '--without-zstd', '--without-isl', '--disable-nls']
        if self.target == 'amd64':
            args += ['--with-arch=nocona', '--with-tune=nocona', '--with-fpmath=sse']
        if self.gomp:
            args.append('--enable-libgomp')
        if self.atomic:
            args.append('--enable-libatomic')
        if self.resume == 'runtime':
            args.append('--no-recursion')
        return args

    def run_logged(self, argv, log, env=None, cwd=None, append=False):
        return logged(argv, log, env, cwd, append=append, quarantine=self.work)

    def build(self):
        self.preflight()
        if self.check:
            return
        work = self.work
        if self.resume == 'no':
            work.mkdir()
            (work / 'build').mkdir(); (work / 'stage').mkdir()
            if self.external:
                self.kernel_receipt = work / 'external-compiler.txt'
                self.kernel_receipt.write_text(self.external_state)
            fields = {'scope': self.scope, 'target': self.target, 'triplet': self.triplet, 'seed_source': self.origin, 'runtime_libraries': self.selection, ('compiler' if self.external else 'kernel'): str(self.kernel), 'sysroot': str(self.sysroot), 'math': str(self.math), 'jobs': self.count, **self.host_fields()}
            receipt = platform.platform() + '\n' + ''.join(key + '=' + value + '\n' for key, value in fields.items())
            receipt += capture([self.tools['gcc'], '--version']) + capture([self.tools['g++'], '--version']) + capture([self.make, '--version'])
            recipe = self.pkgsrc / 'lang/gcc16'
            inputs = [self.archive, recipe / 'distinfo', recipe / 'Makefile', recipe / 'Makefile.common', self.kernel_receipt, self.tools['gcc'], self.tools['g++'], self.tools['readelf']] + [self.math / 'lib' / ('lib' + name + '.a') for name in ('gmp', 'mpfr', 'mpc')] + sorted(path for path in (recipe / 'patches').iterdir() if path.is_file())
            inputs += [self.sysroot / 'usr/include' / name for name in ('stddef.h', 'stdio.h', 'pthread.h', 'math.h')] + [self.sysroot / 'usr/lib' / name for name in ('libc.so.12', 'libpthread.so.1', 'libm.so.0', 'crt0.o')]
            if self.provenance:
                inputs.append(self.provenance)
            (work / 'inputs.txt').write_text(receipt + digest_rows(inputs))
            fields = self.host_fields()
            import shlex
            self.run_logged([fields['host_cc']] + shlex.split(fields['host_cflags']) + ['-I' + str(self.math / 'include'), PROFILE / 'cross/tests/host-gmp.c', self.math / 'lib/libgmp.a', '-o', work / 'host-gmp'], work / 'host-gmp-build.log', self.env)
            self.run_logged([work / 'host-gmp'], work / 'host-gmp.log')
            self.run_logged([work / 'host-gmp', 'timer'], work / 'host-gmp.log', append=True)
            with (work / 'patch.log').open('xb') as output:
                prepare_source(self.pkgsrc, self.archive, work / 'src', quarantine=work, output=output)
        elif self.resume == 'support':
            (work / 'external-compiler.txt').write_text(self.external_state)
            with (work / 'inputs.txt').open('a') as stream:
                stream.write(digest_rows([work / 'external-compiler.txt']))
        else:
            self.backup = backup_resume(self)
        helper_inputs = sorted(HERE.glob('*.py')) + policy_sources()
        helper_inputs += [work / 'src' / name / 'configure' for name in ('gcc', 'libstdc++-v3', 'libgomp', 'libatomic')] + [work / 'src/configure', Path(self.make)]
        with (work / 'inputs.txt').open('a') as stream:
            stream.write('target_binutils=' + ('external-compiler-prefix' if self.external else 'audited-kernel-prefix') + '\n')
            for name in TOOLS:
                stream.write(digest_rows([self.tools[name]]) + capture([self.tools[name], '--version']).splitlines()[0] + '\n')
            stream.write(digest_rows(helper_inputs))
        if self.resume != 'support':
            self.run_logged([work / 'src/configure'] + self.configure_args(), work / 'configure.log', self.env, work / 'build')
        if self.external:
            build_external(self)
            (work / 'external-support').mkdir()
            for name in 'libgcc.mvars specs tconfig.h version.h auto-host.h Makefile config.status'.split():
                shutil.copy2(work / 'build/gcc' / name, work / 'external-support' / name)
            with (work / 'inputs.txt').open('a') as stream:
                stream.write(digest_rows(sorted((work / 'external-support').iterdir()) + [work / 'external-runtime-plan.txt']))
        else:
            if self.resume == 'runtime':
                verify_frontend(self.backup)
            else:
                self.run_logged([self.make, '-j' + self.count, 'all-gcc'], work / 'frontends.log', self.env, work / 'build')
            version = self.compiler_version(work / 'build/gcc/xgcc')
            (work / 'frontend-version.txt').write_text(version)
            require('Thread model: posix' in version.splitlines(), 'Runtime compiler does not select POSIX threads')
            libraries = ['libgcc', 'libstdc++-v3'] + (['libgomp'] if self.gomp else []) + (['libatomic'] if self.atomic else [])
            self.run_logged([self.make, '-j' + self.count] + ['all-target-' + name for name in libraries], work / 'runtime-build.log', self.env, work / 'build')
            if self.resume == 'runtime':
                verify_frontend(self.backup)
            self.run_logged([self.make, 'DESTDIR=' + str(work / 'stage')] + ['install-target-' + name for name in libraries], work / 'runtime-install.log', self.env, work / 'build')
            if self.resume == 'runtime':
                verify_frontend(self.backup)
        runtime = work / 'stage/usr/pkg/gcc16'
        for name in ('crtbegin.o', 'crtbeginS.o', 'crtend.o', 'crtendS.o'):
            self.check_elf(runtime / 'lib/gcc' / self.triplet / VERSION / name, work / 'stage')
        for soname in self.sonames:
            self.check_elf(runtime / 'lib' / soname, work / 'stage')
            dynamic = capture([self.tools['readelf'], '-d', runtime / 'lib' / soname])
            (work / (soname + '.dynamic')).write_text(dynamic)
            require(any('SONAME' in line and '[' + soname + ']' in line for line in dynamic.splitlines()), 'Runtime SONAME mismatch')
            require(not any(str(path) in dynamic for path in (work, self.sysroot, self.kernel, self.math)), 'Build-host path leaked into runtime dynamic tags')
        require((runtime / 'include/c++/vector').is_file() and (runtime / 'include/c++' / self.triplet / 'bits/c++config.h').is_file(), 'Missing installed C++ headers')
        manifests(work / 'stage', work)
        if self.external:
            require(compiler_state(self) == (work / 'external-compiler.txt').read_text(), 'External compiler changed during build')
        (work / 'build-success').write_text(self.scope + '\n')
        print('Staged target runtime: ' + str(runtime) + '\nThis is not a complete gcc16 package or runtime acceptance.')
