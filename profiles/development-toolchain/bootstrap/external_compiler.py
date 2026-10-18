# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; existing POSIX GCC16 owns every target object.
from pathlib import Path
import os
import shutil
from host import *
from runtime import field
from runtime_libraries import check_prior
from support_resume import support


def compiler_state(state):
    require(state.resume in ('no', 'support'), 'External compiler does not support frontend resume')
    require(not state.gomp and not state.atomic, 'External mode currently builds libgcc and libstdc++ only')
    for name in ('gcc', 'g++'):
        require('Thread model: posix' in state.compiler_version(state.tools[name]).splitlines(), 'External compiler must use POSIX threads')
    frontends = []
    for compiler, name in [('gcc', 'cc1'), ('g++', 'cc1plus')]:
        path = Path(capture([state.tools[compiler], '-print-prog-name=' + name]).strip()).resolve(strict=True)
        require(os.access(path, os.X_OK) and paths.inside(path, state.kernel), 'External compiler frontend missing or escapes prefix')
        frontends.append(path)
    return 'compiler_mode=external-posix\nversion=16.2.0\ntriplet=' + state.triplet + '\nthread_model=posix\nsupport_target=gcc-leaf-metadata-v1\ntarget_objects=external-compiler\ncompiler=' + str(state.kernel) + '\ncc1=' + str(frontends[0]) + '\ncc1plus=' + str(frontends[1]) + '\n' + digest_rows([state.tools['gcc'], state.tools['g++']] + frontends)


def check_support_resume(state):
    work = state.work
    inputs = (work / 'inputs.txt').read_text()
    check_prior(work, state.selection, state.resume)
    expected = {'scope': 'runtime-only-external-compiler', 'target': state.target, 'triplet': state.triplet, 'seed_source': state.origin, 'compiler': str(state.kernel), 'sysroot': str(state.sysroot), 'math': str(state.math), 'jobs': state.count, **state.host_fields()}
    for key, value in expected.items():
        require(field(inputs, key) == value, 'Support resume input changed: ' + key)
    prior = (work / 'external-compiler.txt').read_text().replace('support_target=libgcc-support\n', 'support_target=gcc-leaf-metadata-v1\n')
    require(state.external_state == prior, 'External compiler changed before support resume')
    makefile = (work / 'build/Makefile').read_text().splitlines()
    require(all(line in makefile for line in ['CFLAGS_FOR_TARGET = ' + state.target_flags, 'CXXFLAGS_FOR_TARGET = ' + state.target_flags, 'LDFLAGS_FOR_TARGET = -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-z,relro']), 'Support target flags changed')
    require(digest_rows([state.make]) in inputs, 'Support GNU make provider changed')
    support('check' if state.check else 'resume', work)


def build_external(state):
    work, make = state.work, state.make
    env = dict(state.env)
    host_targets = 'configure-gcc all-libiberty all-libcpp all-libdecnumber all-libbacktrace all-build-libiberty all-build-libcpp all-build-fixincludes all-fixincludes'.split()
    state.run_logged([make, '-j' + state.count] + host_targets, work / 'support-host.log', env, work / 'build')
    state.run_logged([make, '-C', work / 'build/gcc', '-j' + state.count, 'GCC_FOR_TARGET=' + str(state.tools['gcc']) + ' --sysroot=' + str(state.sysroot), 'libgcc.mvars', 'tconfig.h', 'machmode.h', 'mode-classes.def', 'version.h'], work / 'support-build.log', env, work / 'build')
    for name in ('cc1', 'cc1plus'):
        require(paths.entry(work / 'build/gcc' / name) is None, 'External runtime mode unexpectedly built frontend')
    (work / 'build/gcc/include').mkdir(parents=True, exist_ok=True)
    build_triplet = capture(['sh', work / 'src/config.guess']).strip()
    env['CC'] = str(state.tools['gcc']) + ' --sysroot=' + str(state.sysroot) + ' -B' + str(work / 'build/gcc') + '/'
    env['CXX'] = env['CC'] + ' -shared-libgcc -nostdinc++'
    env.update(CFLAGS=state.target_flags, CXXFLAGS=state.target_flags, CPPFLAGS='', LDFLAGS='-L' + str(work / 'stage/usr/pkg/gcc16/lib') + ' -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-z,relro')
    for name in TOOLS:
        env[name.upper()] = state.env[name.upper() + '_FOR_TARGET']
    (work / 'external-runtime-plan.txt').write_text('support_target=gcc-leaf-metadata-v1\ntarget_objects=external-compiler\n' + ''.join(key + '=' + env[key] + '\n' for key in ('CC', 'CXX', 'LDFLAGS')))
    for library in ('libgcc', 'libstdc++-v3'):
        directory = work / 'build' / state.triplet / library
        directory.mkdir(parents=True, exist_ok=True)
        args = ['--build=' + build_triplet, '--host=' + state.triplet, '--target=' + state.triplet, '--with-cross-host=' + build_triplet, '--with-target-subdir=' + state.triplet, '--prefix=/usr/pkg/gcc16', '--libdir=/usr/pkg/gcc16/lib', '--with-toolexeclibdir=/usr/pkg/gcc16/lib', '--disable-multilib', '--enable-shared', '--enable-threads=posix', '--disable-nls']
        if library == 'libstdc++-v3':
            args += ['--with-gxx-include-dir=/usr/pkg/gcc16/include/c++', '--enable-long-long', '--disable-libstdcxx-pch', '--disable-libssp']
        state.run_logged([work / 'src' / library / 'configure'] + args, work / (library + '-configure.log'), env, directory)
        require('CC = ' + env['CC'] in (directory / 'Makefile').read_text().splitlines(), 'Target library lost selected external compiler')
        state.run_logged([make, '-j' + state.count, 'all'], work / (library + '-build.log'), env, directory)
        state.run_logged([make, 'DESTDIR=' + str(work / 'stage'), 'install'], work / (library + '-install.log'), env, directory)
