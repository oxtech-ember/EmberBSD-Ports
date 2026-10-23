# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); upstream standalone GCC16 Fortran components.
"""Create the real component argv. The producer must validate and lock inputs."""
from pathlib import Path
import re
import shlex
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] /
                       'pkgsrc/lang/gcc16-fortran-runtime/files'))
from fortran_target import components

VERSION = '16.2.0'
TARGETS = {'amd64': ('x86_64--netbsd', '-O2 -march=nocona -mtune=nocona -mfpmath=sse'),
           'aarch64': ('aarch64--netbsd', '-O2')}
TOOLS = 'ar as ld nm objcopy objdump ranlib readelf strip'.split()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def absolute(value):
    path = Path(value)
    require(path.is_absolute() and '..' not in path.parts, 'Use an absolute canonical input path')
    return path


def component_plan(target, build_triplet, source, work, compiler, sysroot,
                   make, jobs, native_cc):
    """Keep the top-level compiler and the accepted base runtime out of make."""
    require(target in TARGETS, 'Unsupported target')
    triplet, flags = TARGETS[target]
    require(re.fullmatch(r'[A-Za-z0-9_]+-[A-Za-z0-9_.-]+', build_triplet)
            and build_triplet != triplet, 'Use the actual distinct build triplet')
    require(type(jobs) is int and jobs > 0, 'Jobs must be a positive integer')
    source, work, compiler, sysroot, make, native_cc = map(
        absolute, (source, work, compiler, sysroot, make, native_cc))
    gcc = sysroot / 'usr/pkg/gcc16'
    support = gcc / 'lib/gcc' / triplet / VERSION
    common = ['--sysroot=' + str(sysroot), '-B' + str(support) + '/',
              '-B' + str(gcc / 'lib') + '/']
    def command(name):
        return shlex.join([str(compiler / 'bin' / (triplet + '-' + name))] + common)
    env = {'CC': command('gcc'), 'FC': command('gfortran'),
           'F77': command('gfortran'), 'GFORTRAN': command('gfortran'),
           'CC_FOR_BUILD': shlex.quote(str(native_cc)),
           'CFLAGS': flags + ' -fPIC', 'FCFLAGS': flags + ' -fPIC',
           'FFLAGS': flags + ' -fPIC',
           'CPPFLAGS': shlex.quote('-I' + str(gcc / 'include/c++' / triplet / 'bits')),
           'LDFLAGS': shlex.join(['-Wl,-rpath,/usr/pkg/gcc16/lib', '-Wl,-z,relro']),
           'CONFIG_SITE': '/dev/null'}
    env.update({name.upper(): str(compiler / 'bin' / (triplet + '-' + name))
                for name in TOOLS})
    shared = ['--build=' + build_triplet, '--host=' + triplet,
              '--target=' + triplet, '--with-target-subdir=' + triplet,
              '--disable-multilib', '--enable-shared', '--enable-static']
    package = ['--with-cross-host=' + build_triplet, '--prefix=/usr/pkg/gcc16', '--libdir=/usr/pkg/gcc16/lib',
               '--with-toolexeclibdir=/usr/pkg/gcc16/lib']
    result = []
    # GCC Makefile.def configures libgfortran after these real target libraries.
    # libbacktrace stays a PIC convenience archive and has no install action.
    for name in components(target):
        args = shared + (['--enable-host-shared'] if name == 'libbacktrace' else package)
        directory = work / 'build' / triplet / name
        result.append({'component': name, 'phase': 'configure', 'cwd': str(directory),
                       'argv': [str(source / name / 'configure')] + args, 'env': dict(env)})
        result.append({'component': name, 'phase': 'build', 'cwd': str(directory),
                       'argv': [str(make), '-j' + str(jobs), 'V=1', 'all'], 'env': dict(env)})
        if name != 'libbacktrace':
            result.append({'component': name, 'phase': 'install', 'cwd': str(directory),
                           'argv': [str(make), 'DESTDIR=' + str(work / 'stage'), 'V=1', 'install'],
                           'env': dict(env)})
    return result
