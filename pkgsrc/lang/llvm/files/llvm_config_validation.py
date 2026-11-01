#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Validate target metadata through host llvm-config.
"""Check that a host llvm-config reports the installed target LLVM package."""
import json
from pathlib import Path
import re
import shlex
import subprocess

VERSION = '23.1.4'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def definitions(path):
    return {m[1]: m[2].strip() for line in Path(path).read_text().splitlines()
            if (m := re.fullmatch(r'#define ([A-Z][A-Z0-9_]*) (.+)', line))}


def string(values, name):
    result = json.loads(values[name])
    require(isinstance(result, str), 'unsupported target macro ' + name)
    return result


def normalized_triple(value):
    parts = value.split('-')
    if len(parts) >= 3 and not parts[1]:
        parts[1] = 'unknown'
    return '-'.join(parts)


def target_path(path, sysroot):
    require(any(path == root or path.startswith(root + '/')
                for root in ('/usr/pkg', '/usr/lib', '/lib')),
            'target LLVM linker flags contain a non-installed path: ' + path)
    return str(Path(sysroot) / path.lstrip('/'))


def target_ldflags(values, sysroot):
    result = []
    for flag in shlex.split(string(values, 'LLVM_LDFLAGS')):
        if flag.startswith('-L/'):
            flag = '-L' + target_path(flag[2:], sysroot)
        elif flag.startswith('-R/'):
            flag = '-R' + target_path(flag[2:], sysroot)
        elif flag.startswith('-Wl,'):
            parts = flag[4:].split(',')
            for index, part in enumerate(parts):
                if part.startswith('-R/'):
                    parts[index] = '-R' + target_path(part[2:], sysroot)
                elif part.startswith('-rpath='):
                    parts[index] = '-rpath=' + target_path(part[len('-rpath='):], sysroot)
            flag = '-Wl,' + ','.join(parts)
        elif flag.startswith('-L') or any('/' + marker in flag for marker in ('WRKDIR', 'WRKSRC', 'tmp/')):
            raise ValueError('target LLVM linker flags retain a build path: ' + flag)
        result.append(flag)
    return ' '.join(result)


def validate_llvm_config(config, sysroot):
    config = Path(config).resolve(strict=True)
    sysroot = Path(sysroot).resolve(strict=True)
    prefix = sysroot / 'usr/pkg'
    cmake_path = prefix / 'lib/cmake/llvm/LLVMConfig.cmake'
    require(cmake_path.is_file(), 'target llvm-devel is not installed')
    cmake = cmake_path.read_text()
    version = re.search(r'^set\(LLVM_PACKAGE_VERSION\s+([^ )]+)\)', cmake, re.M)
    host_triple = re.search(r'^set\(LLVM_HOST_TRIPLE\s+"([^"]+)"\)', cmake, re.M)
    targets = re.search(r'^set\(LLVM_TARGETS_TO_BUILD\s+([^)]*)\)', cmake, re.M)
    assertions = re.search(r'^set\(LLVM_ENABLE_ASSERTIONS\s+(ON|OFF)\)', cmake, re.M)
    require(version and version[1] == VERSION and host_triple and targets and assertions,
            'installed target LLVM CMake metadata is incomplete')
    header = definitions(prefix / 'include/llvm/Config/llvm-config.h')
    require(string(header, 'LLVM_HOST_TRIPLE') == host_triple[1] and
            string(header, 'LLVM_DEFAULT_TARGET_TRIPLE') == host_triple[1],
            'installed target LLVM triple metadata disagrees')
    metadata = prefix / 'lib/cmake/llvm/emberbsd'
    variables = definitions(metadata / 'BuildVariables.inc')
    for name in ('LibraryDependencies.inc', 'ExtensionDependencies.inc', 'llvm-config.cpp'):
        require((metadata / name).is_file(), 'target llvm-devel metadata is missing: ' + name)
    expected_targets = ' '.join(targets[1].split(';'))
    expected_rtti = 'YES' if variables.get('LLVM_HAS_RTTI') == '1' else 'NO'
    args = [
        '--version', '--host-target', '--prefix', '--includedir', '--libdir',
        '--targets-built', '--assertion-mode', '--has-rtti', '--link-shared',
        '--shared-mode', '--ldflags',
    ]
    result = subprocess.run([str(config), *args], check=True, capture_output=True, text=True)
    rows = result.stdout.splitlines()
    require(len(rows) == 10, 'llvm-config returned an incomplete target query set')
    expected = [
        VERSION, normalized_triple(string(header, 'LLVM_DEFAULT_TARGET_TRIPLE')),
        str(prefix), str(prefix / 'include'), str(prefix / 'lib'), expected_targets,
        assertions[1], expected_rtti,
    ]
    require(rows[:8] == expected, 'llvm-config does not match the installed target LLVM metadata')
    expected_ldflags = ' '.join(['-L' + str(prefix / 'lib'), target_ldflags(variables, sysroot)])
    require(rows[8] == expected_ldflags,
            'llvm-config linker flags do not match the installed target sysroot')
    require(rows[9] == 'shared', 'llvm-config shared mode does not match package metadata')
    libs = subprocess.run([str(config), '--libs', 'core', 'executionengine', 'orcjit', 'native'],
                          check=True, capture_output=True, text=True).stdout.strip()
    require(libs, 'llvm-config returned no component libraries')
    libfiles_text = subprocess.run([str(config), '--libfiles', 'core'],
                                   check=True, capture_output=True, text=True).stdout
    libfiles = shlex.split(libfiles_text)
    require(libfiles and all(Path(path).is_file() and Path(path).is_relative_to(prefix / 'lib')
                             for path in libfiles),
            'llvm-config returned missing or non-target library files')
    return rows
