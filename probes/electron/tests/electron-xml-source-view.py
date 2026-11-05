#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check XML pair migration, interruption, and vendor-header exclusion."""
import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name, filename):
    spec=importlib.util.spec_from_file_location(name,owner/filename)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
view=load('view','protobuf-source-view.py'); components=load('compression','compression-source-view.py')
names=('libxml','libxslt')
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve(); source=root/'source'; dest=root/'view'; origin=source/'third_party'
    selected=dest/'src/third_party'; origin.mkdir(parents=True); selected.mkdir(parents=True)
    unbundle=source/'build/linux/unbundle'; unbundle.mkdir(parents=True)
    (unbundle/'replace_gn_files.py').write_text("REPLACEMENTS = {'libxml': 'third_party/libxml/BUILD.gn', 'libxslt': 'third_party/libxslt/BUILD.gn'}\n")
    for name in names:
        component=origin/name; (component/'src/include').mkdir(parents=True)
        (component/'src/include/vendor.h').write_text('bundled')
        (component/'BUILD.gn').write_text('vendor')
        (component/'chromium').mkdir(); (component/'chromium/keep.cc').write_text('retained')
        (unbundle/(name+'.gn')).write_text('source_set("'+name+'") {}\n')
        (selected/name).symlink_to(component,target_is_directory=True)
    (origin/'libxml/linux/include').mkdir(parents=True)
    (origin/'libxml/linux/include/config.h').write_text('bundled')
    neighbor=selected/'zlib'; neighbor.write_text('preserve')
    before=(neighbor.stat().st_ino,neighbor.stat().st_mtime_ns)
    actual=components.verify_view
    def fail_new(*args):
        if len(args)==4 and args[3]==names: raise ValueError('interrupted')
        return actual(*args)
    with patch.object(components,'verify_view',side_effect=fail_new):
        try: components.activate(view,source,dest,lambda:None,names,'xml-components')
        except ValueError: pass
        else: raise AssertionError('interruption ignored')
    assert (root/'.view.xml-components-migration').is_file()
    def old(): assert all((selected/n).is_symlink() for n in names)
    components.activate(view,source,dest,old,names,'xml-components')
    assert (neighbor.stat().st_ino,neighbor.stat().st_mtime_ns)==before
    components.verify_view(view,source,dest,names)
    for name in names:
        assert not (selected/name/'src').exists()
        assert (selected/name/'chromium/keep.cc').is_file()
    assert not (selected/'libxml/linux/include').exists()
    (selected/'libxslt/BUILD.gn').unlink(); (selected/'libxslt/BUILD.gn').write_text('foreign')
    try: components.verify_view(view,source,dest,names)
    except ValueError: pass
    else: raise AssertionError('mixed XML view accepted')
print('PASS: XML pair transaction preserves siblings, recovers and masks bundled headers')
