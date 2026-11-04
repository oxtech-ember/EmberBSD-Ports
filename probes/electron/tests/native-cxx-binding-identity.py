#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Ensure versioned native adapters track both SDK ABI header paths and bytes."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
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
# Platform host and target LLVM runtime are independently selectable.
with tempfile.TemporaryDirectory(prefix='electron-platform-binding-') as temporary:
    root = Path(temporary)
    native = SimpleNamespace(host={'os': 'Darwin', 'cpu': 'arm64'},
        command=lambda name: ['/prefix/bin/' + name],
        abi_flags={name: [] for name in ('cppflags', 'cflags', 'cxxflags', 'ldflags')})
    original_bind = build.bind_versioned
    captured = []
    build.bind_versioned = lambda sdk, native, parent, record: captured.append(record) or {'cxx': 'bound'}
    options = SimpleNamespace(work=root, host_runtime_root=None, target_runtime_stage=Path('/target-stage'),
                              host_compiler_family='clang')
    assert build.native_runtime_binding(options, {}, native, {}, {}) == {'cxx': 'bound'}
    assert 'native_cxx_runtime' not in captured[0]
    assert captured[0]['commands']['cxx'] == ['/prefix/bin/cxx']
    options.host_runtime_root, options.target_runtime_stage = Path('/native'), None
    try:
        build.native_runtime_binding(options, {}, native, {}, {})
        raise AssertionError('accepted incomplete hardened runtime selection')
    except ValueError as error:
        assert 'requires both native and target' in str(error)
    build.bind_versioned = original_bind
print('native bindings distinguish platform and hardened C++ runtime')
