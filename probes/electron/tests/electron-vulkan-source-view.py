#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Test common Vulkan source projection and interrupted recovery."""
import importlib.util
import tempfile
from pathlib import Path
from unittest.mock import patch

owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files'
def load(name, file):
    spec = importlib.util.spec_from_file_location(name, owner / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
view = load('view', 'protobuf-source-view.py')
projection = load('compression', 'compression-source-view.py')
names = ('vulkan-loader', 'vulkan-headers')
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp).resolve()
    source, destination = root / 'source', root / 'view'
    origin, selected = source / 'third_party', destination / 'src/third_party'
    origin.mkdir(parents=True); selected.mkdir(parents=True)
    registry = root / 'native/share/vulkan/registry'; registry.mkdir(parents=True)
    (registry / 'vk.xml').write_text('common')
    unbundle = source / 'build/linux/unbundle'; unbundle.mkdir(parents=True)
    (unbundle / 'replace_gn_files.py').write_text('REPLACEMENTS = ' + repr({name: 'third_party/' + name + '/src/BUILD.gn' for name in names}))
    for name in names:
        component = origin / name; vendor = component / 'src'; vendor.mkdir(parents=True)
        (vendor / 'BUILD.gn').write_text('bundled')
        (vendor / 'include').mkdir(); (vendor / 'include/private.h').write_text('bundled')
        if name == 'vulkan-headers':
            (vendor / 'registry').mkdir(); (vendor / 'registry/vk.xml').write_text('bundled')
        (unbundle / (name + '.gn')).write_text('source_set("test") {}\n')
        (selected / name).symlink_to(component, target_is_directory=True)
    neighbor = selected / 'unrelated'; neighbor.write_text('keep')
    before = (neighbor.stat().st_ino, neighbor.stat().st_mtime_ns)
    actual = projection.verify_view
    def interrupted(*args, **kwargs):
        if len(args) == 4 and args[3] == names: raise ValueError('interrupted')
        return actual(*args, **kwargs)
    with patch.object(projection, 'verify_view', side_effect=interrupted):
        try: projection.activate(view, source, destination, lambda: None, names, 'vulkan-components', registry=registry)
        except ValueError: pass
        else: raise AssertionError('interruption ignored')
    assert (root / '.view.vulkan-components-migration').is_file()
    projection.activate(view, source, destination, lambda: None, names, 'vulkan-components', registry=registry)
    projection.verify_view(view, source, destination, names, registry=registry)
    assert (neighbor.stat().st_ino, neighbor.stat().st_mtime_ns) == before
    for name in names:
        assert not (selected / name / 'src/include').exists()
        assert (selected / name / 'src/BUILD.gn').is_symlink()
    assert (selected / 'vulkan-headers/src/registry').resolve() == registry
    assert (selected / 'vulkan-headers/src/registry/vk.xml').read_text() == 'common'
    (selected / 'vulkan-loader/src/foreign').write_text('bad')
    try: projection.verify_view(view, source, destination, names, registry=registry)
    except ValueError: pass
    else: raise AssertionError('foreign file accepted')
print('PASS Vulkan loader/headers projection, owned registry, recovery and vendor exclusion')
