#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check one canonical export per change of selected recipe inputs."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile

owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron', owner)
electron = importlib.util.module_from_spec(spec); spec.loader.exec_module(electron)
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp).resolve(); (root/'scripts').mkdir(); work=root/'work'; work.mkdir()
    (root/'state').write_text('one')
    (root/'scripts/pkgsrc-source-identity.py').write_text('''\ndef git_package_identity(root, name, git):\n return {'package':name, 'value':(root/'state').read_text()}\ndef equivalent_effective_package(a,b):\n return a==b\n''')
    calls=[]
    def capture(command, **kwargs):
        calls.append(command)
        export=Path(command[3])
        for name in ('archivers/brotli','archivers/zstd','devel/zlib','archivers/minizip-ng','multimedia/ffmpeg9'):
            recipe=export/name; recipe.mkdir(parents=True)
            (recipe/'distinfo').write_text(name + (root/'state').read_text())
        return SimpleNamespace(stdout=b'')
    sdk={'process':SimpleNamespace(capture=capture)}
    native=SimpleNamespace(tool=lambda name:'/selected/'+name)
    o=SimpleNamespace(ports_source=root,work=work,git='/selected/git',ml_patch='/selected/patch',phase='configure')
    with patch.object(electron,'selected_control_git',return_value='/selected/git'):
        first=electron.compression_recipe_catalog(o,sdk,native,{})
        assert len(calls)==1 and len(first['recipes'])==2
        (work/'configuration.json').write_text(json.dumps({'environment':{'EMBERBSD_COMPRESSION_RECIPE_CATALOG':json.dumps(first)}}))
        o.phase='build'
        assert electron.compression_recipe_catalog(o,sdk,native,{})==first and len(calls)==1
        # Reconfigure binds in scratch but must reuse the real work receipt.
        scratch=root/'scratch'; scratch.mkdir()
        o.phase='reconfigure'; o.native_binding_root=work; o.work=scratch
        assert electron.compression_recipe_catalog(o,sdk,native,{})==first and len(calls)==1
        o.shared_minizip=True; o.shared_ffmpeg=True
        combined=electron.compression_recipe_catalog(o,sdk,native,{})
        assert len(calls)==2 and set(combined['recipes']) == {
            'archivers/brotli','archivers/zstd','devel/zlib','archivers/minizip-ng','multimedia/ffmpeg9'}
        (work/'configuration.json').write_text(json.dumps({'environment':{'EMBERBSD_COMPRESSION_RECIPE_CATALOG':json.dumps(combined)}}))
        assert electron.compression_recipe_catalog(o,sdk,native,{}) == combined and len(calls)==2
        (root/'state').write_text('two')
        o.phase='build'
        try: electron.compression_recipe_catalog(o,sdk,native,{})
        except ValueError as error: assert 'reconfigure' in str(error)
        else: raise AssertionError('changed owner accepted by build')
        o.phase='reconfigure'
        changed=electron.compression_recipe_catalog(o,sdk,native,{})
        assert len(calls)==3 and changed['recipes']!=combined['recipes']
print('PASS: one canonical batch per effective owner change, unchanged build reuses catalog')
