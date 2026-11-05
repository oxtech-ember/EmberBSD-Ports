#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise role-specific FFmpeg selection and reject missing or stale packages."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron', owner)
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve(); host = root/'host'; target = root/'sysroot'; buildlink = root/'buildlink'
    pkgpath = 'multimedia/ffmpeg9'; modules = ('libavcodec', 'libavformat', 'libavutil')
    hp = host/'pkgdb/ffmpeg9-9.0.2nb6'; tp = target/'usr/pkg/pkgdb/ffmpeg9-9.0.2nb6'
    for pkg, suffix in ((hp, '.dylib'), (tp, '.so')):
        pkg.mkdir(parents=True)
        entries = [entry for name in modules for entry in
                   ('lib/ffmpeg9/pkgconfig/'+name+'.pc', 'lib/ffmpeg9/'+name+suffix)]
        entries.append('include/ffmpeg9/libavutil/version.h')
        content = entries + ['@comment MD5:' + hashlib.md5(b'owned', usedforsecurity=False).hexdigest()]
        (pkg/'+CONTENTS').write_text('\n'.join(content))
        for meta in ('+BUILD_INFO', '+BUILD_VERSION'): (pkg/meta).write_text('owned')
        prefix = host if pkg == hp else target/'usr/pkg'
        for entry in entries:
            path=prefix/entry; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('owned')
    inputs = {}
    for name in modules:
        path = host/'lib/ffmpeg9/pkgconfig'/(name+'.pc'); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('native pc'); inputs[str(path)] = {}
        path = buildlink/'lib/pkgconfig'/(name+'.pc'); path.parent.mkdir(parents=True, exist_ok=True); path.write_text('view pc')
    selection = root/'selection'; selection.mkdir()
    (selection/'selection.json').write_text(json.dumps({'identity': {'inputs': inputs}}))
    environments = []
    def capture(command, env):
        environments.append(env)
        return SimpleNamespace(stdout=b'63.1\n63.1\n61.1\n')
    sdk = {'process': SimpleNamespace(capture=capture)}
    native = SimpleNamespace(tool=lambda role: '/selected/'+role, host={'os':'Darwin'})
    options = SimpleNamespace(shared_ffmpeg=True, host_prefix=host, sysroot=target,
        host_buildlink_pkgsrc=root/'pkgsrc', _common_native_packages={pkgpath:[hp]},
        _common_target_packages={pkgpath:[tp]}, _compression_catalog={'recipes':{pkgpath:{'distinfo':'verified'}}})
    env = {'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK':str(selection)}
    with patch.object(e, 'validate_package_source') as validate:
        values=e.common_ffmpeg(options, sdk, native, env, buildlink)
        assert values['use_system_ffmpeg'] and not values['is_component_ffmpeg']
        assert all(x.endswith('.dylib') for x in values['emberbsd_ffmpeg_host_libraries'])
        assert all(x.endswith('.so') for x in values['emberbsd_ffmpeg_target_libraries'])
        assert len(values['emberbsd_ffmpeg_host_inputs']) == 7
        assert validate.call_count == 2
        assert len(env['EMBERBSD_FFMPEG_SOURCE_SHA256']) == 64
        assert 'PKG_CONFIG_SYSROOT_DIR' not in environments[0]
        assert environments[1]['PKG_CONFIG_SYSROOT_DIR'] == str(target)
        assert environments[1]['PKG_CONFIG_LIBDIR'].split(':')[0] == str(target/'usr/pkg/lib/ffmpeg9/pkgconfig')
        options._common_native_packages[pkgpath] = []
        try: e.common_ffmpeg(options, sdk, native, env, buildlink)
        except ValueError as error: assert 'missing' in str(error)
        else: raise AssertionError('missing native package accepted')
        options._common_native_packages[pkgpath] = [hp]
        inputs.pop(next(iter(inputs))); (selection/'selection.json').write_text(json.dumps({'identity':{'inputs':inputs}}))
        try: e.common_ffmpeg(options, sdk, native, env, buildlink)
        except ValueError as error: assert 'not selected' in str(error)
        else: raise AssertionError('unselected native pkg-config accepted')
    assert e.common_ffmpeg(SimpleNamespace(shared_ffmpeg=False), sdk, native, {}, None) == {}
print('PASS: matching host/target FFmpeg, explicit pkg-config roles, missing and unselected inputs')
