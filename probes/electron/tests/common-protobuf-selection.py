#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check common source identity, package versions and selected protoc."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_electron', owner / 'electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
with tempfile.TemporaryDirectory(prefix='electron-protobuf-selection-') as tmp:
    root = Path(tmp); source = root / 'source'; source.mkdir()
    (source / 'version.json').write_text(json.dumps({'36.x': {'protoc_version': '36.2'}}))
    repo = root / 'repo'; (repo / 'scripts/source-inputs/protobuf').mkdir(parents=True)
    (repo / 'scripts/source-inputs/protobuf/source.py').touch()
    recipe = repo / 'pkgsrc/devel/protobuf'; (recipe / 'patches').mkdir(parents=True)
    (recipe / 'patches/patch-test').write_text('patch')
    (recipe / 'distinfo').write_text('distinfo')
    export = root / 'export/devel/protobuf'; (export / 'patches').mkdir(parents=True)
    (export / 'patches/patch-test').write_text('patch'); (export / 'distinfo').write_text('distinfo')
    view = root / 'view'; (view / 'bin').mkdir(parents=True)
    host = root / 'host'; (host / 'bin').mkdir(parents=True)
    protoc = host / 'bin/protoc-36.2'; protoc.write_text('fake'); protoc.chmod(0o755)
    (view / 'bin/protoc').symlink_to(protoc)
    patch_hash = hashlib.sha256(b'patch').hexdigest(); dist_hash = hashlib.sha256(b'distinfo').hexdigest()
    def metadata(package, content, include_distinfo=True):
        package.mkdir(parents=True)
        (package / '+CONTENTS').write_text(content + '\n')
        (package / '+BUILD_INFO').write_text('PKGPATH=devel/protobuf\n')
        text = 'devel/protobuf/patches/patch-test: ' + patch_hash + '\n'
        if include_distinfo: text += 'devel/protobuf/distinfo: ' + dist_hash + '\n'
        (package / '+BUILD_VERSION').write_text(text)
    host_package = host / 'pkgdb/protobuf-36.2nb3'; metadata(host_package, 'bin/protoc-36.2')
    target_db = root / 'target/usr/pkg/pkgdb'
    metadata(target_db / 'protobuf-36.2nb4', 'lib/libprotobuf.so')
    metadata(target_db / 'protobuf-devel-36.2nb4', 'include/google/protobuf/message.h', False)
    (target_db / 'protobuf-devel-36.2nb4/+BUILD_INFO').write_text('PKGPATH=devel/protobuf-devel\n')
    selection = root / 'selection'; selection.mkdir()
    (selection / 'selection.json').write_text(json.dumps({'identity': {'inputs': {str(host_package / '+BUILD_INFO'): 'sha'}}}))
    options = SimpleNamespace(protobuf_source=source, protobuf_ports_source=repo,
        protobuf_archive=root/'archive', protobuf_patch=root/'patch', sdk_source=root/'sdk',
        git=Path('/usr/bin/git'), sysroot=root/'target', host_prefix=host, host_buildlink_pkgsrc=root/'export')
    native = SimpleNamespace(tool=lambda name: '/selected/' + name)
    state = dict(identity={'tree_sha256': 'a', 'identity': {'patches': ['first']}},
                 host='36.2.0', target='36.2.0', protoc='libprotoc 36.2')
    class Process:
        @staticmethod
        def capture(command, *, env):
            if 'verify-source' in command:
                output = json.dumps(state['identity'])
            elif '--modversion' in command:
                output = state['host'] if '--define-prefix' in command else state['target']
            elif '-E' in command:
                output = 'protobuf-devel-36.2nb4' if command[-1].startswith('protobuf-devel') else 'protobuf-36.2nb4'
            elif '--version' in command:
                output = state['protoc']
            else:
                raise AssertionError(command)
            return SimpleNamespace(stdout=output.encode())
    sdk = {'process': Process()}
    def selected():
        env = {'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK': str(selection)}; args = build.common_protobuf(options, sdk, native, env, str(view), root/'runtime')
        return args, env
    args, first = selected(); assert args['emberbsd_common_protobuf'] and args['emberbsd_protoc'] == str(protoc.resolve())
    original_time = (source / 'version.json').stat().st_mtime_ns
    state['identity']['identity']['patches'] = ['second']
    _, second = selected()
    assert first['EMBERBSD_PROTOBUF_SOURCE_SHA256'] != second['EMBERBSD_PROTOBUF_SOURCE_SHA256']
    assert (source / 'version.json').stat().st_mtime_ns == original_time
    old_patch = (recipe / 'patches/patch-test').stat().st_mtime_ns
    (recipe / 'patches/patch-test').write_text('other')
    import os
    os.utime(recipe / 'patches/patch-test', ns=(old_patch, old_patch))
    try:
        selected(); raise AssertionError('accepted mismatched common patch bytes')
    except ValueError as error:
        assert 'patch inventory differs' in str(error)
    (recipe / 'patches/patch-test').write_text('patch')
    (host_package / '+BUILD_VERSION').write_text('devel/protobuf/patches/patch-test: ' + '0'*64 + '\n' + 'devel/protobuf/distinfo: ' + dist_hash + '\n')
    try:
        selected(); raise AssertionError('accepted stale selected package patch')
    except ValueError as error:
        assert 'package patch inventory differs' in str(error)
    metadata_text = 'devel/protobuf/patches/patch-test: ' + patch_hash + '\n' + 'devel/protobuf/distinfo: ' + dist_hash + '\n'
    (host_package / '+BUILD_VERSION').write_text(metadata_text)
    devel_info = target_db / 'protobuf-devel-36.2nb4/+BUILD_VERSION'
    saved_devel = devel_info.read_text(); devel_info.write_text('')
    try:
        selected(); raise AssertionError('accepted missing target SDK patch metadata')
    except ValueError as error:
        assert 'package patch inventory differs' in str(error)
    devel_info.write_text(saved_devel)
    for field, wrong in (('host', '35.0'), ('target', '35.0'), ('protoc', 'libprotoc 35.0')):
        old = state[field]; state[field] = wrong
        try:
            selected(); raise AssertionError('accepted mismatched ' + field)
        except ValueError:
            pass
        state[field] = old
    try:
        build.common_protobuf(options, sdk, native, {}, None, root/'runtime')
        raise AssertionError('accepted missing host buildlink')
    except ValueError:
        pass
    options.protobuf_source = None
    try:
        build.common_protobuf(options, sdk, native, {}, str(view), root/'runtime')
        raise AssertionError('accepted partial common source input')
    except ValueError:
        pass
    options.protobuf_ports_source = options.protobuf_archive = options.protobuf_patch = None
    assert build.common_protobuf(options, sdk, native, {}, None, None) == {}
print('PASS: common protobuf identity, package/protoc version and default controls')
