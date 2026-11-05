# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Project only selected target package headers into the Electron source view."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

_spec = importlib.util.spec_from_file_location('electron_header_projection', Path(__file__).with_name('ml-source-projection.py'))
projection = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(projection)
NAMES = ('eigen3', 'flatbuffers', 'fp16')
SUBDIR = {'eigen3': Path('src'), 'flatbuffers': Path('src/include/flatbuffers'),
          'fp16': Path('src/include')}


def component(view, origin, path, name, identity, sourceprep):
    view.require(path.is_dir() and not path.is_symlink(), 'header component is not local: '+name)
    outer = view.entries(origin/name, {'src'})
    view.require({p.name for p in path.iterdir()} == set(outer) | {'src'}, 'header component entries changed: '+name)
    for entry, item in outer.items():
        link = path/entry
        view.require(link.is_symlink() and os.readlink(link) == str(item), 'header integration link changed: '+str(link))
    if name == 'flatbuffers':
        src = path/'src'
        view.require({p.name for p in src.iterdir()} == {'include', 'src'} and
                     {p.name for p in (src/'include').iterdir()} == {'flatbuffers'} and
                     (src/'src').is_dir() and not any((src/'src').iterdir()),
                     'FlatBuffers header view changed')
    elif name == 'fp16':
        view.require({p.name for p in (path/'src').iterdir()} == {'include'}, 'FP16 header view changed')
    projection.validate_projection(sourceprep, path/SUBDIR[name], package='electron-view/header-'+name,
                                   identity={'installed_package': identity})


def verify_view(view, source, destination, selected, sourceprep):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    origin, root = source/'third_party', destination/'src/third_party'
    view.require(set(selected) == set(NAMES), 'incomplete target header selection')
    for name in NAMES:
        component(view, origin, root/name, name, selected[name]['identity'], sourceprep)
    return destination/'src'


def activate(view, source, destination, selected, inventory, sourceprep, verify_old_whole, *, old_identities=None):
    """Migrate legacy links or update changed package projections transactionally."""
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    origin, root = source/'third_party', destination/'src/third_party'
    view.require(set(selected) == set(NAMES), 'incomplete target header selection')
    for name in NAMES:
        view.require(selected[name].get('destination') == str(Path('third_party')/name/SUBDIR[name]),
                     'target header destination differs: '+name)
    identities = {name: selected[name]['identity'] for name in NAMES}
    if old_identities is None:
        names = list(NAMES)
    else:
        view.require(set(old_identities) == set(NAMES), 'partial old header selection')
        names = [name for name in NAMES if old_identities[name] != identities[name]]
        if not names:
            return verify_view(view, source, destination, selected, sourceprep)
    marker = destination.parent/('.'+destination.name+'.header-components-migration')
    if old_identities is not None and not os.path.lexists(marker):
        try:
            return verify_view(view, source, destination, selected, sourceprep)
        except Exception:
            pass
    choice = hashlib.sha256(json.dumps({'old':old_identities, 'new':identities},sort_keys=True).encode()).hexdigest()
    def check_old(path, name, partial):
        if old_identities is None:
            return path.is_symlink() and os.readlink(path) == str(origin/name)
        if partial:
            return path.is_dir() and not path.is_symlink()
        component(view, origin, path, name, old_identities[name], sourceprep)
        return True
    def build(name, path):
        path.mkdir()
        for entry, item in view.entries(origin/name, {'src'}).items():
            (path/entry).symlink_to(item, target_is_directory=item.is_dir())
        target = path/SUBDIR[name]
        target.parent.mkdir(parents=True, exist_ok=True)
        if name == 'flatbuffers':
            (path/'src/src').mkdir()
        data = selected[name]
        base = Path(data['root'])
        # `files` are package-prefix relative; strip the selected subtree.
        pkgprefix = Path(data['package']).parents[1]
        mapped = {}
        for relative in data['files']:
            absolute = pkgprefix/relative
            rel = absolute.relative_to(base).as_posix()
            mapped[rel] = {'path':str(absolute), 'md5':data['expected_md5'][relative],
                           'stable':data['stable'][relative]}
        previous = (root if old_identities is not None else origin)/name/SUBDIR[name]
        projection.prepare_selected_projection(inventory, previous, mapped, target, sourceprep=sourceprep,
            package='electron-view/header-'+name, identity={'installed_package':identities[name]})
    def verify_new(migration):
        return verify_view(view, source, destination, selected, sourceprep)
    return view.sibling_component_transaction(destination, origin, names, choice, 'header-components',
        verify_old_whole, build, verify_new, check_old_entry=check_old,
        already_new=lambda: old_identities is None and all((root/name).is_dir() and not (root/name).is_symlink() for name in NAMES))
