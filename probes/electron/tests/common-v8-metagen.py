#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify selected metagen providers and compiler roles."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
import tempfile

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_electron', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
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
                           v8_metagen_runtime_view=view, v8_source=root, work=root,
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
    # Reconfigure computes inputs in a temporary binding directory but must
    # keep the descriptor under the persistent producer work root.
    opts.native_binding_root = root
    opts.work = root / 'scratch'
    scratch_result = build.common_v8_metagen(*args)
    assert scratch_result == result
    assert str(root / 'v8-metagen-selection.json') in scratch_result['v8_metagen_runtime_inputs']
    opts.work = root
    del opts.native_binding_root
    # The override namespace changes independently of its tracked payload set.
    class JsonIO:
        @staticmethod
        def write_json(path, value, exclusive=False):
            Path(path).write_text(json.dumps(value, sort_keys=True))
    package = prefix / 'pkgdb/runtime'
    package.mkdir()
    (package / '+BUILD_INFO').write_text('PKGPATH=converters/libiconv\n')
    (package / '+CONTENTS').write_text(str(runtime_library.relative_to(prefix)) + '\n')
    opts.v8_metagen_runtime_extra = [runtime_library]
    build.write_v8_metagen_selection(root, {'jsonio': JsonIO()}, opts.v8_metagen_selection)
    descriptor = root / 'v8-metagen-selection.json'
    first_mtime = descriptor.stat().st_mtime_ns
    build.write_v8_metagen_selection(root, {'jsonio': JsonIO()}, opts.v8_metagen_selection)
    assert descriptor.stat().st_mtime_ns == first_mtime
    (view / 'library').unlink()
    (view / 'other-alias').symlink_to(runtime_library)
    changed_alias = build.common_v8_metagen(*args)
    assert changed_alias['v8_metagen_runtime_inputs'] == result['v8_metagen_runtime_inputs']
    build.write_v8_metagen_selection(root, {'jsonio': JsonIO()}, opts.v8_metagen_selection)
    assert json.loads(descriptor.read_text()) == {
        'version': 1, 'aliases': {'other-alias': 'lib/runtime.dylib'},
        'extra': ['lib/runtime.dylib']}
    ninja = os.environ.get('EMBERBSD_TEST_NINJA')
    if ninja:
        graph = root / 'build.ninja'
        graph.write_text('rule generate\n  command = cp v8-metagen-selection.json generated\n'
                         'build generated: generate v8-metagen-selection.json\n')
        subprocess.run([ninja, '-f', str(graph)], cwd=root, check=True, capture_output=True)
        before = (root / 'generated').read_text()
        (view / 'other-alias').unlink()
        (view / 'third-alias').symlink_to(runtime_library)
        build.common_v8_metagen(*args)
        build.write_v8_metagen_selection(root, {'jsonio': JsonIO()}, opts.v8_metagen_selection)
        subprocess.run([ninja, '-f', str(graph)], cwd=root, check=True, capture_output=True)
        assert (root / 'generated').read_text() != before
        (view / 'third-alias').unlink()
    else:
        (view / 'other-alias').unlink()
    (view / 'library').symlink_to(runtime_library)
    (package / '+CONTENTS').write_text('')
    try:
        build.common_v8_metagen(*args)
    except ValueError:
        pass
    else:
        raise AssertionError('unowned extra runtime input was accepted')
    opts.v8_metagen_runtime_extra = []
    # Installed platform ABI uses the same owned providers without a stage.
    opts.host_prefix = prefix
    opts.host_runtime_root = None
    assert build.common_v8_metagen(*args) == result
    opts.host_runtime_root = prefix
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
