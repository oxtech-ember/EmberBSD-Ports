#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check the common Darwin runtime producer's CMake inputs."""
import importlib.util
from pathlib import Path
import shlex
from types import SimpleNamespace
import sys
files = Path(__file__).resolve().parents[1] / 'files'
spec = importlib.util.spec_from_file_location('native_runtime', files / 'native.py')
sys.path.insert(0, str(files))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
native = SimpleNamespace(host={'cpu': 'arm64'}, path='/host/bin:/host/sbin',
                         tool=lambda name: '/host/bin/' + name)
bindings = {'CC': '/work/native-commands/cc', 'CXX': '/work/native-commands/cxx'}
cmd = mod.cmake_arguments(Path('/source'), Path('/work'), Path('/host'), Path('/sdk'), '26.0', native, bindings)
options = dict(arg[2:].split('=', 1) for arg in cmd if arg.startswith('-D'))
spaced = mod.cmake_arguments(Path('/source'), Path('/work'), Path('/host'), Path('/sdk with spaces'), '26.0', native, bindings)
spaced_options = dict(arg[2:].split('=', 1) for arg in spaced if arg.startswith('-D'))
assert shlex.split(spaced_options['CMAKE_SHARED_LINKER_FLAGS']) == [
    '-Wl,-reexport_library,/sdk with spaces/usr/lib/libc++abi.tbd']
assert cmd[:3] == ['/host/bin/cmake', '-S', '/source/runtimes']
assert options['CMAKE_C_COMPILER'] == bindings['CC']
assert options['CMAKE_CXX_COMPILER'] == bindings['CXX']
assert options['CMAKE_LINKER'] == '/host/bin/ld'
assert options['CMAKE_SHARED_LINKER_FLAGS'] == '-Wl,-reexport_library,/sdk/usr/lib/libc++abi.tbd'
assert options['CMAKE_OSX_SYSROOT'] == '/sdk'
assert options['CMAKE_OSX_DEPLOYMENT_TARGET'] == '26.0'
assert options['CMAKE_OSX_ARCHITECTURES'] == 'arm64'
assert options['CMAKE_INSTALL_NAME_DIR'] == '/host/lib/libc++'
assert options['CMAKE_BUILD_WITH_INSTALL_NAME_DIR'] == 'ON'
assert options['CMAKE_BUILD_WITH_INSTALL_RPATH'] == 'ON'
assert options['CMAKE_INSTALL_NAME_TOOL'] == '/host/bin/llvm-install-name-tool'
assert options['CMAKE_LIPO'] == '/host/bin/llvm-lipo'
assert options['CMAKE_LIBTOOL'] == '/host/bin/llvm-libtool-darwin'
assert options['LLVM_ENABLE_RUNTIMES'] == 'libcxx'
assert options['LIBCXX_CXX_ABI'] == 'system-libcxxabi'
assert options['LIBCXX_CXX_ABI_INCLUDE_PATHS'] == '/sdk/usr/include/c++/v1'
assert options['LIBCXX_HARDENING_MODE'] == 'extensive'
assert options['LIBCXX_ABI_VERSION'] == '1'
assert options['LIBCXX_ABI_NAMESPACE'] == '__ember1'
assert options['LIBCXX_SHARED_OUTPUT_NAME'] == 'c++_ember1'
assert options['LIBCXX_INSTALL_INCLUDE_DIR'] == 'include/libc++/v1'
assert options['LIBCXX_INSTALL_INCLUDE_TARGET_DIR'] == 'include/libc++/v1'
assert options['LIBCXX_INSTALL_LIBRARY_DIR'] == 'lib/libc++'
for feature in ('SHARED', 'STATIC', 'FILESYSTEM', 'LOCALIZATION', 'EXCEPTIONS', 'RTTI'):
    assert options['LIBCXX_ENABLE_' + feature] == 'ON'
print('Darwin native runtime CMake selection PASS')

class SDKError(Exception):
    pass
mod.owner.require = lambda condition, message: None if condition else (_ for _ in ()).throw(SDKError(message))
fixture = '''Load command 1
          cmd LC_ID_DYLIB
         name /host/lib/libc++/libc++_ember1.1.dylib (offset 24)
Load command 2
          cmd LC_REEXPORT_DYLIB
         name /usr/lib/libc++abi.dylib (offset 24)
Load command 3
          cmd LC_LOAD_DYLIB
         name /usr/lib/libSystem.B.dylib (offset 24)
'''
mod.validate_darwin_load_commands(fixture, Path('/host'))
for invalid in (fixture.replace('/host/lib/libc++/libc++_ember1.1.dylib', '@rpath/libc++_ember1.1.dylib'),
                fixture.replace('LC_REEXPORT_DYLIB', 'LC_LOAD_DYLIB'),
                fixture.replace('/usr/lib/libSystem.B.dylib', '/tmp/foreign.dylib')):
    try:
        mod.validate_darwin_load_commands(invalid, Path('/host'))
    except SDKError:
        pass
    else:
        raise AssertionError('accepted wrong install name or dependencies')
print('Darwin dylib identity and ABI load command checks PASS')
