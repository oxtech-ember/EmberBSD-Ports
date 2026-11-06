# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Project verified SPIRV-Tools source and the consumer's GN wrapper."""
import hashlib
import json
import os
from pathlib import Path

NAME = 'spirv-tools'
PACKAGE = 'parallel/spirv-tools'


def selection(view, sourceprep, source):
    original = Path(source)
    view.require(original.is_absolute() and original.is_dir() and not original.is_symlink(),
                 'invalid SPIRV-Tools source directory')
    root = original.resolve(strict=True)
    receipt = sourceprep.read_prepared_tree_receipt(str(root), package=PACKAGE)
    sourceprep.validate_prepared_tree(str(root), package=PACKAGE, identity=receipt['identity'])
    record = root / sourceprep.PREPARED_TREE_RECEIPT
    def stable(st):
        return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    before = stable(record.stat()); raw = record.read_bytes()
    view.require(stable(record.stat()) == before, 'SPIRV-Tools receipt changed during verification')
    return {'path': str(root), 'tree_sha256': receipt['tree_sha256'],
            'receipt_sha256': hashlib.sha256(raw).hexdigest()}


def component(view, origin, path, selected, wrapper, *, verify):
    expected = {p.name for p in origin.iterdir()}
    view.require('src' in expected, 'SPIRV-Tools source component is missing')
    if verify:
        view.require(path.is_dir() and not path.is_symlink(), 'SPIRV-Tools component is not local')
        view.require({p.name for p in path.iterdir()} == expected, 'SPIRV-Tools component entries changed')
    else:
        path.mkdir()
    for entry in origin.iterdir():
        dest = path / entry.name
        if entry.name == 'src':
            view.dependency_view(Path(selected['path']), dest, {Path('BUILD.gn'): wrapper}, set(), verify=verify)
        elif verify:
            view.require(dest.is_symlink() and os.readlink(dest) == str(entry), 'SPIRV-Tools link changed')
        else:
            dest.symlink_to(entry, target_is_directory=entry.is_dir())


def verify_view(view, source, destination, selected, sourceprep):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    view.require(selection(view, sourceprep, selected['path']) == selected, 'SPIRV-Tools selection changed')
    wrapper = source / 'build/linux/unbundle/vulkan-SPIRV-Tools.gn'
    component(view, source / 'third_party' / NAME, destination / 'src/third_party' / NAME,
              selected, wrapper, verify=True)
    return destination / 'src'


def activate(view, source, destination, selected, old, sourceprep, verify_old):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    origin = source / 'third_party'
    marker = destination.parent / ('.' + destination.name + '.spirv-components-migration')
    if old == selected:
        view.require(not os.path.lexists(marker), 'unexpected SPIRV-Tools migration marker')
        return verify_view(view, source, destination, selected, sourceprep)
    identity = hashlib.sha256(json.dumps({'old': old, 'new': selected}, sort_keys=True).encode()).hexdigest()
    wrapper = source / 'build/linux/unbundle/vulkan-SPIRV-Tools.gn'
    def check_old(path, name, partial):
        if old is None:
            return path.is_symlink() and os.readlink(path) == str(origin / name)
        if partial:
            return path.is_dir() and not path.is_symlink()
        component(view, origin / name, path, old, wrapper, verify=True)
        return True
    def build(name, path):
        component(view, origin / name, path, selected, wrapper, verify=False)
    return view.sibling_component_transaction(
        destination, origin, [NAME], identity, 'spirv-components', verify_old, build,
        lambda _: verify_view(view, source, destination, selected, sourceprep),
        check_old_entry=check_old, already_new=lambda: False)
