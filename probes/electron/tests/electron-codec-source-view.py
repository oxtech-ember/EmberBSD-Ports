#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check codec migration, interruption, and vendor-header exclusion."""
import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name, filename):
    spec=importlib.util.spec_from_file_location(name,owner/filename)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
view=load('view','protobuf-source-view.py'); components=load('compression','compression-source-view.py')
names=('dav1d','libaom','libvpx','opus','flac')
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve(); source=root/'source'; dest=root/'view'; origin=source/'third_party'
    selected=dest/'src/third_party'; origin.mkdir(parents=True); selected.mkdir(parents=True)
    unbundle=source/'build/linux/unbundle'; unbundle.mkdir(parents=True)
    (unbundle/'replace_gn_files.py').write_text('REPLACEMENTS = '+repr({n:'third_party/'+n+'/BUILD.gn' for n in names})+'\n')
    for name in names:
        component=origin/name; hidden={'dav1d':'libdav1d', 'libaom':'source/libaom', 'libvpx':'source/libvpx', 'opus':'src', 'flac':'src'}[name]
        (component/hidden).mkdir(parents=True)
        (component/hidden/'vendor.h').write_text('bundled')
        (component/'BUILD.gn').write_text('vendor')
        (component/'chromium').mkdir(); (component/'chromium/keep.cc').write_text('retained')
        (unbundle/(name+'.gn')).write_text('source_set("'+name+'") {}\n')
        (selected/name).symlink_to(component,target_is_directory=True)
    neighbor=selected/'zlib'; neighbor.write_text('preserve')
    before=(neighbor.stat().st_ino,neighbor.stat().st_mtime_ns)
    actual=components.verify_view
    def fail_new(*args):
        if len(args)==4 and args[3]==names: raise ValueError('interrupted')
        return actual(*args)
    with patch.object(components,'verify_view',side_effect=fail_new):
        try: components.activate(view,source,dest,lambda:None,names,'codec-components')
        except ValueError: pass
        else: raise AssertionError('interruption ignored')
    assert (root/'.view.codec-components-migration').is_file()
    def old(): assert all((selected/n).is_symlink() for n in names)
    components.activate(view,source,dest,old,names,'codec-components')
    assert (neighbor.stat().st_ino,neighbor.stat().st_mtime_ns)==before
    components.verify_view(view,source,dest,names)
    for name in names:
        assert not (selected/name/({'dav1d':'libdav1d','libaom':'source/libaom','libvpx':'source/libvpx','opus':'src','flac':'src'}[name])).exists()
        assert (selected/name/'chromium/keep.cc').is_file()
    (selected/'libvpx/BUILD.gn').unlink(); (selected/'libvpx/BUILD.gn').write_text('foreign')
    try: components.verify_view(view,source,dest,names)
    except ValueError: pass
    else: raise AssertionError('mixed codec view accepted')
print('PASS: codec transaction preserves siblings, recovers and masks bundled headers')
