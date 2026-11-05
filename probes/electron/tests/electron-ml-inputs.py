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
    setattr(options, 'ml_ruy_source', None)
    try:
        m.common_ml_sources(options, sdk, native, env)
    except ValueError:
        pass
    else:
        raise AssertionError('missing common ML source accepted')
print('PASS: mandatory owner-verified ML sources')
