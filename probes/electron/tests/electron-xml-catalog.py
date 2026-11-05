#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""XML/XSLT extend the existing single recipe-catalog export."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
p=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',p); e=importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve(); (root/'scripts').mkdir(); work=root/'work'; work.mkdir()
    (root/'scripts/pkgsrc-source-identity.py').write_text('''
def git_package_identity(root, name, git): return {"package":name}
def equivalent_effective_package(a,b): return a==b
''')
    names=('archivers/brotli','archivers/zstd','textproc/libxml2','textproc/libxslt'); calls=[]
    def capture(command,**kwargs):
        calls.append(command); dest=Path(command[3])
        for name in names:
            recipe=dest/name; recipe.mkdir(parents=True); (recipe/'distinfo').write_text(name)
        return SimpleNamespace(stdout=b'')
    sdk={'process':SimpleNamespace(capture=capture)}; native=SimpleNamespace(tool=lambda name:'/selected/'+name)
    o=SimpleNamespace(ports_source=root,work=work,git='/selected/git',ml_patch='/selected/patch',phase='configure',shared_xml=True)
    with patch.object(e,'selected_control_git',return_value='/selected/git'):
        catalog=e.compression_recipe_catalog(o,sdk,native,{})
        assert set(catalog['recipes'])==set(names) and len(calls)==1
        (work/'configuration.json').write_text(json.dumps({'environment':{'EMBERBSD_COMPRESSION_RECIPE_CATALOG':json.dumps(catalog)}}))
        o.phase='build'; assert e.compression_recipe_catalog(o,sdk,native,{})==catalog and len(calls)==1
print('PASS: XML/XSLT share the existing single recipe export and cached build selection')
