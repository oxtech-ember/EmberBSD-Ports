#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check a selected Quick3D CMake build before using it for host tools."""
from pathlib import Path
import sys
import re


def read_cache(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*):[A-Z]+=(.*)', line)
        if not match:
            continue
        name, value = match.groups()
        if name in result:
            raise ValueError('duplicate CMake cache key: ' + name)
        result[name] = value
    return result


def check(directory, work, prefix, cc, cxx, deployment, runtime_cmake):
    directory, work, prefix = Path(directory), Path(work), Path(prefix)
    if not directory.is_absolute() or not (directory/'build.ninja').is_file():
        raise ValueError('missing selected Quick3D build')
    current = read_cache(directory/'CMakeCache.txt')
    base = read_cache(work/'qtbase/CMakeCache.txt')
    expected = {
        'CMAKE_HOME_DIRECTORY': str(work/'source/qtquick3d-everywhere-src-6.12.0'),
        'CMAKE_C_COMPILER': cc, 'CMAKE_CXX_COMPILER': cxx,
        'CMAKE_PREFIX_PATH': str(prefix),
        'Qt6_DIR': str(work/'qtbase/lib/cmake/Qt6'),
        'Qt6BuildInternals_DIR': str(work/'qtbase/lib/cmake/Qt6BuildInternals'),
        'CMAKE_PROJECT_TOP_LEVEL_INCLUDES': runtime_cmake,
        'CMAKE_GENERATOR': 'Ninja', 'QT_BUILD_TESTS': 'OFF',
        'QT_BUILD_EXAMPLES': 'OFF', 'QT_FEATURE_system_assimp': 'ON',
        'TEST_quick3d_assimp': 'TRUE',
    }
    for key, value in expected.items():
        if current.get(key) != value:
            raise ValueError('Quick3D configuration mismatch: ' + key)
    if deployment and current.get('CMAKE_OSX_DEPLOYMENT_TARGET') != deployment:
        raise ValueError('Quick3D deployment target mismatch')
    keys = ['TEST_architecture_arch', 'CMAKE_BUILD_TYPE', 'CMAKE_C_FLAGS',
            'CMAKE_CXX_FLAGS', 'CMAKE_C_FLAGS_RELEASE', 'CMAKE_CXX_FLAGS_RELEASE',
            'CMAKE_EXE_LINKER_FLAGS', 'CMAKE_SHARED_LINKER_FLAGS', 'CMAKE_MODULE_LINKER_FLAGS']
    if deployment:
        keys += ['CMAKE_OSX_ARCHITECTURES', 'CMAKE_OSX_SYSROOT', 'CMAKE_OSX_DEPLOYMENT_TARGET']
    for key in keys:
        if key not in base or current.get(key) != base[key]:
            raise ValueError('Quick3D differs from selected Qtbase: ' + key)
    cmake_root = (prefix/'lib/cmake').resolve()
    if not cmake_root.is_relative_to(prefix.resolve()):
        raise ValueError('Quick3D CMake root escapes selected prefix')
    for package in ('assimp', 'embree', 'TinyEXR', 'meshoptimizer', 'xatlas'):
        value = Path(current.get(package + '_DIR', ''))
        if not value.is_absolute() or not value.is_dir() or not value.resolve().is_relative_to(cmake_root):
            raise ValueError('Quick3D provider mismatch: ' + package)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 8:
            raise ValueError('usage: check-quick3d-cache.py BUILD WORK PREFIX CC CXX DEPLOYMENT RUNTIME_CMAKE')
        check(*sys.argv[1:])
    except (OSError, ValueError) as error:
        print('Qt Quick3D reuse: ' + str(error), file=sys.stderr)
        sys.exit(1)
