#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify selected metagen providers and compiler roles."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_electron', owner / 'electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    prefix = root / 'stage'
    sdkroot = root / 'sdk'
    script = sdkroot / 'scripts/run-darwin-with-runtime.py'
    script.parent.mkdir(parents=True)
    script.touch()
    lib = prefix / 'lib/libclang.dylib'
    bindings = prefix / 'share/clang-python-bindings'
    for f in (lib, bindings / 'clang/cindex.py', bindings / 'clang/__init__.py'):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.touch()
    for name, pkgpath, files in (
        ('clang', 'lang/clang', [lib]),
        ('bindings', 'lang/clang-python-bindings', [bindings / 'clang/cindex.py', bindings / 'clang/__init__.py'])):
        package = prefix / 'pkgdb' / name
        package.mkdir(parents=True)
        (package / '+BUILD_INFO').write_text('PKGPATH=' + pkgpath + '\n')
        (package / '+CONTENTS').write_text(''.join(str(f.relative_to(prefix)) + '\n' for f in files))
    view = root / 'view'
    view.mkdir()
    runtime_library = prefix / 'lib/runtime.dylib'
    runtime_library.touch()
    (view / 'library').symlink_to(runtime_library)
    host = root / 'host'
    target = root / 'target'
    for directory, flag in ((host, '--host-flag'), (target, '--target-flag')):
        directory.mkdir()
        (directory / 'commands.json').write_text(json.dumps({'test_flag': flag}))
        (directory / 'cxx').touch()
    opts = SimpleNamespace(v8_metagen_libclang_so=lib, v8_metagen_bindings_dir=bindings,
                           v8_metagen_runtime_view=view, v8_source=root,
                           host_runtime_root=prefix, compiler_family='clang', sdk_source=sdkroot)
    class Process:
        @staticmethod
        def capture(*args, **kwargs):
            return SimpleNamespace(stdout=json.dumps([str(script)]).encode())
    class Bindings:
        @staticmethod
        def compiler_argv(record, role, args):
            assert role == 'cxx' and args == ['-c']
            return ['/compiler', record['test_flag'], '-c']
    native = SimpleNamespace(host={'os': 'Darwin'}, tool=lambda name: '/selected/' + name)
    args = (opts, {'process': Process(), 'compiler_bindings': Bindings()}, native,
            {'BUILD_CXX': str(host / 'cxx')}, {'cxx': str(target / 'cxx')})
    result = build.common_v8_metagen(*args)
    assert result['v8_metagen_extra_flags'] == ['--target-flag']
    assert result['v8_metagen_host_extra_flags'] == ['--host-flag']
    assert result['v8_metagen_gn_executable'] == '/selected/gn'
    assert str(script) in result['v8_metagen_runtime_inputs']
    replacement = prefix / 'lib/replacement.dylib'
    replacement.touch()
    (view / 'library').unlink()
    (view / 'library').symlink_to(replacement)
    changed = build.common_v8_metagen(*args)
    assert changed['v8_metagen_runtime_inputs'] != result['v8_metagen_runtime_inputs']
    (view / 'library').unlink()
    (view / 'library').symlink_to(script)
    try:
        build.common_v8_metagen(*args)
    except ValueError:
        pass
    else:
        raise AssertionError('external runtime library was accepted')
    (view / 'library').unlink()
    (view / 'library').symlink_to(runtime_library)
    (prefix / 'pkgdb/clang/+CONTENTS').write_text('')
    try:
        build.common_v8_metagen(*args)
    except ValueError:
        pass
    else:
        raise AssertionError('unowned libclang was accepted')
    opts.v8_metagen_bindings_dir = None
    try:
        build.common_v8_metagen(*args)
    except ValueError:
        pass
    else:
        raise AssertionError('partial selection was accepted')
print('PASS: selected V8 metagen providers and compiler roles')
