#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Ensure versioned native adapters track both SDK ABI header paths and bytes."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / 'electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
with tempfile.TemporaryDirectory(prefix='electron-native-binding-identity-') as temporary:
    root = Path(temporary)
    sdk_file = root / 'sdk.py'
    sdk_file.write_text('sdk')
    headers = root / 'sdk/usr/include/c++/v1'
    headers.mkdir(parents=True)
    (headers / 'cxxabi.h').write_text('first')
    (headers / '__cxxabi_config.h').write_text('config')
    include = root / 'runtime/include'
    library = root / 'runtime/lib'
    include.mkdir(parents=True)
    library.mkdir(parents=True)
    (include / '__config_site').write_text('#define _LIBCPP_ABI_NAMESPACE __ember1\n#define _LIBCPP_HARDENING_MODE_DEFAULT 16\n')
    build.hardening_header(root / 'runtime', 'include', '__ember1')
    for bad in ('__ember1wrong', '__1'):
        (include / '__config_site').write_text('#define _LIBCPP_ABI_NAMESPACE ' + bad + '\n#define _LIBCPP_HARDENING_MODE_DEFAULT 16\n')
        try:
            build.hardening_header(root / 'runtime', 'include', '__ember1')
        except Exception:
            pass
        else:
            raise AssertionError('unexpected namespace accepted')
    (include / '__config_site').write_text('#define _LIBCPP_ABI_NAMESPACE __ember1\n#define _LIBCPP_HARDENING_MODE_DEFAULT 16bad\n')
    try:
        build.hardening_header(root / 'runtime', 'include', '__ember1')
    except Exception:
        pass
    else:
        raise AssertionError('invalid hardening accepted')
    (include / '__config_site').write_text('__ember1')
    (library / 'libc++_ember1.1.dylib').write_text('runtime')
    python = root / 'python'
    python.touch()
    binding = SimpleNamespace(__file__=str(sdk_file), NATIVE_CXX_RUNTIME_BINDING_API=1,
                              NATIVE_CXX_PLATFORM_ABI_API=1,
                              bind_compilers=lambda destination, **kwargs: destination)
    sdk = {'compiler_bindings': binding}
    native = SimpleNamespace(tool=lambda name: str(python))
    record = {'commands': {}, 'flags': {}, 'link_flags': {},
              'native_cxx_runtime': {'sysroot': str(root / 'sdk'), 'platform_cxxabi': True,
                                     'include_dir': str(include), 'library_dir': str(library)}}
    def select():
        return build.bind_versioned(sdk, native, root / 'bindings', record)
    first = select()
    assert select() == first
    (headers / 'cxxabi.h').write_text('second')
    second = select()
    assert second != first
    replacement = headers / 'other'
    replacement.write_text('second')
    (headers / 'cxxabi.h').unlink()
    (headers / 'cxxabi.h').symlink_to(replacement)
    third = select()
    assert third != second
    (include / '__config_site').write_text('__other')
    fourth = select()
    assert fourth != third
    (library / 'libc++_ember1.1.dylib').write_text('new-runtime')
    assert select() != fourth
native = SimpleNamespace(host={'os': 'Darwin', 'cpu': 'arm64'}, tool=lambda name: '/host/bin/' + name)
options = SimpleNamespace(target='amd64', compiler_family='clang', host_compiler_family='clang',
    sysroot=Path('/target'), host_prefix=Path('/host'), sdk_source=Path('/sdk'),
    xcode_version_plist=Path('/xcode'), macos_sdk=Path('/macos'), macos_minimum='26.0')
tools = {'strip': '/target/strip', 'objcopy': '/target/objcopy'}
original_local_module = build.local_module
build.local_module = lambda name, file: SimpleNamespace(select=lambda native: {'arguments': {}})
default_args = build.arguments(options, native, tools, '1.0', 'launcher')
assert default_args['use_custom_libcxx'] is True
assert 'emberbsd_pkg_config_role' not in default_args
assert build.native_runtime_binding(options, {}, native, {}, {}) is None
for host_root, target_stage in ((Path('/native'), None), (None, Path('/target-stage'))):
    options.host_runtime_root, options.target_runtime_stage = host_root, target_stage
    try:
        build.native_runtime_binding(options, {}, native, {}, {})
        raise AssertionError('accepted partial external libc++ selection')
    except ValueError as error:
        assert 'requires both native and target' in str(error)
options.host_runtime_root, options.target_runtime_stage = Path('/native'), Path('/target-stage')
assert build.arguments(options, native, tools, '1.0', 'launcher')['use_custom_libcxx'] is False
old = ['clang++', '-nostdinc++', '-isystem', '/sdk/include/c++/v1', '-isystem', '/host/lib/clang/23/include', '-DOTHER']
assert build.prefer_chromium_libcxx_headers(old) == ['clang++', '-DOTHER']
build.local_module = original_local_module
print('native binding identity tracks selected ABI header paths and bytes')
