#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Selected installed headers replace legacy views without copying siblings."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(sys.argv[1])/'src'))
from emberbsd_sdk import inventory, sourceprep
owner = Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
view=load('view',owner/'protobuf-source-view.py'); headers=load('headers',owner/'header-source-view.py')
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp).resolve(); source=root/'source'; origin=source/'third_party'; origin.mkdir(parents=True)
    selected=root/'view/src/third_party'; selected.mkdir(parents=True); prefix=root/'sysroot/usr/pkg'; db=prefix/'pkgdb'; db.mkdir(parents=True)
    mapping={'eigen3':('include/eigen3','Eigen/Core'), 'flatbuffers':('include/flatbuffers','flatbuffers.h'), 'fp16':('include','fp16.h')}
    data={}
    for name, (subtree, file) in mapping.items():
        (origin/name/headers.SUBDIR[name]).mkdir(parents=True)
        (origin/name/'BUILD.gn').write_text('gn')
        (origin/name/headers.SUBDIR[name]/file).parent.mkdir(parents=True, exist_ok=True)
        (origin/name/headers.SUBDIR[name]/file).write_text('old')
        (selected/name).symlink_to(origin/name, target_is_directory=True)
        real=prefix/subtree/file; real.parent.mkdir(parents=True, exist_ok=True); real.write_text('new-'+name)
        relative=real.relative_to(prefix).as_posix(); package=db/(name+'-1'); package.mkdir()
        data[name]={'root':str(prefix/subtree), 'destination':str(Path('third_party')/name/headers.SUBDIR[name]), 'package':str(package),
            'files':[relative], 'identity':name, 'expected_md5':{relative:hashlib.md5(real.read_bytes()).hexdigest()},
            'stable':{relative:list(inventory.stable_identity(real.stat()))}}
    (prefix/'include/unrelated.h').write_text('unrelated')
    def old(): assert all((selected/name).is_symlink() for name in headers.NAMES)
    headers.activate(view,source,root/'view',data,inventory,sourceprep,old)
    assert (selected/'fp16/src/include/fp16.h').read_text() == 'new-fp16'
    assert not (selected/'fp16/src/include/unrelated.h').exists()
    headers.verify_view(view,source,root/'view',data,sourceprep)
print('PASS: package-owned header projections exclude unrelated includes')
