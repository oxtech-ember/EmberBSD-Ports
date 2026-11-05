#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Common ML sources are mandatory and individually owner-verified once."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import patch
owner = Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron', owner)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve(); ports=root/'ports'
    for name in ('ml-sources', 'litert', 'openxla'):
        path=ports/'scripts/source-inputs'/name/'source.py'; path.parent.mkdir(parents=True); path.touch()
    options=SimpleNamespace(ports_source=ports, sdk_source=root, git=Path('/usr/bin/git'), ml_patch=Path('/usr/bin/patch'), host_buildlink_pkgsrc=root, ml_pkgsrc_export=root, ml_ports_source=ports, ml_export_patch=Path('/usr/bin/patch'))
    for name in m.ML_PROVIDERS:
        path=root/name; path.mkdir()
        setattr(options, 'ml_'+name.replace('-', '_')+'_source', path)
        setattr(options, 'ml_'+name.replace('-', '_')+'_archive', root/(name+'.tar.gz'))
    calls=[]
    class CommandError(Exception):
        def __init__(self, stderr): self.stderr=stderr
    def capture(command, env):
        calls.append(command)
        if 'devel/neon2sse' in command and '--export-patch' not in command:
            raise CommandError(b'shared pkgsrc export was made from different inputs')
        if '--package' in command:
            name=command[command.index('--package')+1]
        else:
            name='devel/'+Path(command[2]).parent.name
        return SimpleNamespace(stdout=json.dumps({'package':name, 'tree_sha256':'a'*64}).encode())
    sdk={'process':SimpleNamespace(capture=capture, CommandError=CommandError)}
    native=SimpleNamespace(tool=lambda role:'/selected/python')
    env={}
    selector=SimpleNamespace(select=lambda *args, **kwargs: {name:{'identity':'b'*64} for name in ('eigen3','flatbuffers','fp16')})
    with patch.object(m, 'local_module', return_value=selector), patch.object(m, 'common_flatc', return_value={'emberbsd_flatc':'/selected/flatc'}):
        values=m.common_ml_sources(options, sdk, native, env)
    assert len(calls)==len(m.ML_PROVIDERS)+1 and values['use_litert_tflite'] is True
    assert sum('--export-patch' in command for command in calls)==1
    assert len(options.ml_identities)==len(m.ML_PROVIDERS)
    original = dict(options.ml_identities)
    # An override owner without its own export must never inherit the frozen
    # common export, including when its verifier needs a temporary export.
    isolated=root/'new-ports'; owner=isolated/'scripts/source-inputs/litert/source.py'
    owner.parent.mkdir(parents=True); owner.touch()
    options.ml_litert_ports_source=isolated
    calls.clear()
    with patch.object(m, 'local_module', return_value=selector), patch.object(m, 'common_flatc', return_value={'emberbsd_flatc':'/selected/flatc'}):
        m.common_ml_sources(options, sdk, native, env)
    litert=[c for c in calls if c[2] == str(owner)]
    assert len(litert)==1 and '--pkgsrc-export' not in litert[0] and '--export-patch' not in litert[0]
    assert all('--pkgsrc-export' in c for c in calls if c[2] != str(owner))
    assert options.ml_identities == original
    # Explicit per-provider export and patch are paired on the slow retry.
    options.ml_litert_pkgsrc_export=root/'new-export'
    options.ml_litert_export_patch=root/'new-patch'
    previous_capture=capture
    def slow_capture(command, env):
        if command[2] == str(owner) and '--export-patch' not in command:
            calls.append(command)
            raise CommandError(b'shared pkgsrc export was made from different inputs')
        return previous_capture(command, env)
    sdk['process'].capture=slow_capture
    calls.clear()
    with patch.object(m, 'local_module', return_value=selector), patch.object(m, 'common_flatc', return_value={'emberbsd_flatc':'/selected/flatc'}):
        m.common_ml_sources(options, sdk, native, env)
    litert=[c for c in calls if c[2] == str(owner)]
    assert len(litert)==2 and all(c[c.index('--pkgsrc-export')+1] == str(root/'new-export') for c in litert)
    assert litert[-1][litert[-1].index('--export-patch')+1] == str(root/'new-patch')
    assert options.ml_identities == original
    options.ml_litert_pkgsrc_export=None
    try:
        m.common_ml_sources(options, sdk, native, env)
    except ValueError as error:
        assert 'export patch requires an export' in str(error)
    else:
        raise AssertionError('provider export patch without export accepted')
    options.ml_litert_export_patch=None
    sdk['process'].capture=capture
    setattr(options, 'ml_ruy_source', None)
    try:
        m.common_ml_sources(options, sdk, native, env)
    except ValueError:
        pass
    else:
        raise AssertionError('missing common ML source accepted')
print('PASS: mandatory owner-verified ML sources')
