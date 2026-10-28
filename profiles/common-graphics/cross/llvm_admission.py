# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Validate a native llvm-config against live target LLVM metadata."""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

import llvm_native as native
import llvm_target as target


def definitions(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        match = re.fullmatch(r'#define ([A-Z][A-Z0-9_]*) (.+)', line)
        if match:
            result[match[1]] = match[2].strip()
    return result


def cache(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        match = re.fullmatch(r'([^#/][^:=]*):[^=]+=(.*)', line)
        if match:
            result[match[1]] = match[2].strip()
    return result


def string(values, key):
    value = json.loads(values[key])
    if not isinstance(value, str):
        raise ValueError('invalid string: ' + key)
    return value


def validate(real, target_build, sysroot, native_build, runtime=None):
    real = Path(real).resolve(strict=True)
    target_build = Path(target_build).resolve(strict=True)
    sysroot = Path(sysroot).resolve(strict=True)
    native_build = Path(native_build).resolve(strict=True)
    if real.is_relative_to(sysroot) or real.is_relative_to(target_build) or native_build.is_relative_to(sysroot):
        raise ValueError('native input resolves inside target tree')
    if not real.is_file() or not os.access(real, os.X_OK):
        raise ValueError('native helper is not executable')
    native_config = native_build / 'bin/llvm-config'
    if not native_config.resolve(strict=True).is_relative_to(native_build):
        raise ValueError('native llvm-config escapes selected native build')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('LD_', 'DYLD_'))}
    triple = subprocess.check_output([str(native_config), '--host-target'], env=env, text=True).strip()
    platform = native.platform(triple)
    if platform == 'darwin':
        native.darwin(str(real), triple)
        command = [str(real)]
    else:
        bundle = real.parent.parent
        libs = (bundle / 'native/lib').resolve(strict=True)
        if not libs.is_relative_to(bundle):
            raise ValueError('native runtime escapes helper root')
        loaders = list(libs.glob('ld-linux*.so*')) + list(libs.glob('ld-*.so*'))
        loaders = sorted({p.resolve(strict=True) for p in loaders})
        if len(loaders) != 1 or not loaders[0].is_relative_to(libs):
            raise ValueError('expected one retained native loader')
        machine = native.machine(triple)
        native.elf(str(real), machine)
        native.elf(str(loaders[0]), machine)
        command = [str(loaders[0]), '--inhibit-cache', '--library-path', str(libs), str(real)]
        env = {k: v for k, v in os.environ.items() if not k.startswith(('LD_', 'DYLD_'))}
        listing = subprocess.check_output([str(loaders[0]), '--inhibit-cache', '--library-path', str(libs), '--list', str(real)], env=env, text=True)
        for path in native.loaded(listing).values():
            resolved = Path(path).resolve(strict=True)
            if not resolved.is_relative_to(libs):
                raise ValueError('native runtime resolves outside retained prefix')
            native.elf(str(resolved), machine)
    def query(*args):
        env = {k: v for k, v in os.environ.items() if not k.startswith(('LD_', 'DYLD_'))}
        return subprocess.check_output([*command, *args], env=env, text=True).strip()
    cache_values = cache(target_build / 'CMakeCache.txt')
    defs = definitions(target_build / 'include/llvm/Config/llvm-config.h')
    config = definitions(target_build / 'include/llvm/Config/config.h')
    variables = definitions(target_build / 'tools/llvm-config/BuildVariables.inc')
    graph = (target_build / 'tools/llvm-config/LibraryDependencies.inc').read_text()
    spec = target.validate(cache_values, defs, graph)
    prefix = sysroot / 'usr/pkg'
    if not prefix.resolve(strict=True).is_relative_to(sysroot):
        raise ValueError('target LLVM prefix escapes sysroot')
    if Path(cache_values['CMAKE_SYSROOT']).resolve(strict=True) != sysroot:
        raise ValueError('target sysroot mismatch')
    if string(defs, 'LLVM_VERSION_STRING') != '23.1.4' or string(config, 'PACKAGE_VERSION') != '23.1.4':
        raise ValueError('target LLVM version mismatch')
    if string(variables, 'LLVM_OBJ_ROOT') != str(target_build) or cache_values.get('CMAKE_INSTALL_PREFIX') != '/usr/pkg':
        raise ValueError('target build or install prefix mismatch')
    if cache_values.get('LLVM_ENABLE_ASSERTIONS') not in ('ON', 'OFF') or any(cache_values.get(key) != 'ON' for key in ('LLVM_BUILD_LLVM_DYLIB', 'LLVM_LINK_LLVM_DYLIB', 'LLVM_ENABLE_RTTI')):
        raise ValueError('target LLVM cache options mismatch')
    if any(variables.get(key) != '1' for key in ('LLVM_ENABLE_DYLIB', 'LLVM_LINK_DYLIB', 'LLVM_HAS_RTTI')):
        raise ValueError('target LLVM options mismatch')
    for name in ('llvm-config.h', 'abi-breaking.h'):
        installed = prefix / 'include/llvm/Config' / name
        if not installed.resolve(strict=True).is_relative_to(prefix.resolve(strict=True)):
            raise ValueError('installed LLVM header escapes target prefix')
        if installed.read_bytes() != (target_build / 'include/llvm/Config' / name).read_bytes():
            raise ValueError('installed LLVM header mismatch: ' + name)
    library = (prefix / 'lib/libLLVM-23.so').resolve(strict=True)
    if not library.is_relative_to((prefix / 'lib').resolve(strict=True)):
        raise ValueError('LLVM library escapes target prefix')
    target.validate_elf(str(library), spec)
    reported_libraries = shlex.split(query('--link-shared', '--libfiles', 'core'))
    if len(reported_libraries) != 1 or Path(reported_libraries[0]).resolve(strict=True) != library:
        raise ValueError('helper shared LLVM library differs from installed target')
    expected = {'--version': '23.1.4', '--prefix': str(prefix),
                '--includedir': str(prefix / 'include'), '--libdir': str(prefix / 'lib'),
                '--has-rtti': 'YES', '--assertion-mode': cache_values['LLVM_ENABLE_ASSERTIONS'],
                '--shared-mode': 'shared'}
    for flag, value in expected.items():
        if query(flag) != value:
            raise ValueError('helper reports wrong ' + flag)
    if target.for_triple(query('--host-target')) != spec:
        raise ValueError('helper target triple mismatch')
    expected_flags = ['-I' + str(prefix / 'include'), *shlex.split(string(variables, 'LLVM_CXXFLAGS'))]
    if shlex.split(query('--cxxflags')) != expected_flags or '-fno-rtti' in expected_flags:
        raise ValueError('helper C++ ABI flags differ from target metadata')
    flags = shlex.split(query('--ldflags'))
    for flag in flags:
        if flag.startswith('-L'):
            path = Path(flag[2:])
            if not path.is_absolute() or not path.resolve(strict=True).is_relative_to(sysroot):
                raise ValueError('helper linker search escapes target sysroot')
    if not query('--link-shared', '--libs', 'core', 'executionengine', 'orcjit', 'native'):
        raise ValueError('target LLVM component set is incomplete')
    return command
