#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Verify Quick3D cache rejects changed Qtbase and compiler configuration."""
import importlib.util
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[1] / 'cross/check-quick3d-cache.py'
spec = importlib.util.spec_from_file_location('qt_cache', owner)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='qt-cache-test-') as tmp:
    root = Path(tmp); work = root/'work'; build = root/'build'; prefix = root/'prefix'
    (work/'qtbase').mkdir(parents=True); build.mkdir(); (build/'build.ninja').touch()
    common = {'TEST_architecture_arch':'arm64', 'CMAKE_BUILD_TYPE':'Release',
        'CMAKE_C_FLAGS':'', 'CMAKE_CXX_FLAGS':'', 'CMAKE_C_FLAGS_RELEASE':'-O2',
        'CMAKE_CXX_FLAGS_RELEASE':'-O2', 'CMAKE_EXE_LINKER_FLAGS':'',
        'CMAKE_SHARED_LINKER_FLAGS':'', 'CMAKE_MODULE_LINKER_FLAGS':'',
        'CMAKE_OSX_ARCHITECTURES':'', 'CMAKE_OSX_SYSROOT':'macosx',
        'CMAKE_OSX_DEPLOYMENT_TARGET':'26.0'}
    values = dict(common, CMAKE_HOME_DIRECTORY=str(work/'source/qtquick3d-everywhere-src-6.12.0'),
        CMAKE_C_COMPILER='/cc', CMAKE_CXX_COMPILER='/cxx', CMAKE_PREFIX_PATH=str(prefix),
        Qt6_DIR=str(work/'qtbase/lib/cmake/Qt6'),
        Qt6BuildInternals_DIR=str(work/'qtbase/lib/cmake/Qt6BuildInternals'),
        CMAKE_PROJECT_TOP_LEVEL_INCLUDES='/runtime.cmake', CMAKE_GENERATOR='Ninja',
        QT_BUILD_TESTS='OFF', QT_BUILD_EXAMPLES='OFF', QT_FEATURE_system_assimp='ON',
        TEST_quick3d_assimp='TRUE')
    for name in ('assimp', 'embree', 'TinyEXR', 'meshoptimizer', 'xatlas'):
        (prefix/'lib/cmake'/name).mkdir(parents=True, exist_ok=True)
        values[name+'_DIR'] = str(prefix/'lib/cmake'/name)
    def write(path, data):
        path.write_text(''.join(f'{key}:STRING={value}\n' for key,value in data.items()))
    write(work/'qtbase/CMakeCache.txt', common)
    args=(str(build), str(work), str(prefix), '/cc', '/cxx', '26.0', '/runtime.cmake')
    write(build/'CMakeCache.txt', values); m.check(*args)
    for key, bad in (('Qt6_DIR','/other/Qt6'), ('Qt6BuildInternals_DIR','/other/internal'),
                     ('TEST_architecture_arch','x86_64'), ('CMAKE_CXX_FLAGS','-stdlib=other'),
                     ('CMAKE_OSX_DEPLOYMENT_TARGET','25.0'), ('QT_BUILD_TESTS','ON'),
                     ('TinyEXR_DIR','/other/TinyEXR')):
        changed=dict(values);changed[key]=bad;write(build/'CMakeCache.txt',changed)
        try: m.check(*args)
        except ValueError: pass
        else: raise AssertionError('accepted changed ' + key)
    foreign=root/'foreign'; foreign.mkdir()
    escape=prefix/'lib/cmake/escape'; escape.symlink_to(foreign)
    for path in (str(prefix/'lib/cmake/../../foreign'), str(escape)):
        changed=dict(values); changed['TinyEXR_DIR']=path; write(build/'CMakeCache.txt',changed)
        try: m.check(*args)
        except ValueError: pass
        else: raise AssertionError('accepted escaped provider path')
    outside = root/'outside'; outside.mkdir()
    other_prefix = root/'other-prefix'; (other_prefix/'lib').mkdir(parents=True)
    (other_prefix/'lib/cmake').symlink_to(outside)
    escaped = dict(values, CMAKE_PREFIX_PATH=str(other_prefix))
    for name in ('assimp', 'embree', 'TinyEXR', 'meshoptimizer', 'xatlas'):
        (outside/name).mkdir()
        escaped[name+'_DIR'] = str(other_prefix/'lib/cmake'/name)
    write(build/'CMakeCache.txt', escaped)
    try: m.check(str(build), str(work), str(other_prefix), '/cc', '/cxx', '26.0', '/runtime.cmake')
    except ValueError: pass
    else: raise AssertionError('accepted escaped CMake root')
print('PASS: Quick3D cache rejects other Qtbase, ABI flags, architecture and providers')
