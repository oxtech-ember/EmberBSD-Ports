# SPDX-License-Identifier: BSD-2-Clause
"""Project verified common libyuv and SRTP public headers into the source view."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

_spec = importlib.util.spec_from_file_location('electron_media_projection', Path(__file__).with_name('ml-source-projection.py'))
projection = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(projection)
NAMES = ('libyuv', 'libsrtp')


def identity(selected, name):
    # Relocation and metadata timestamps do not change public header content.
    record = {'source': selected[name]['source'],
              'headers': {role: selected[name][role]['header_hashes'] for role in ('host', 'target')}}
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def component(view, origin, path, name, ident, sourceprep):
    view.require(path.is_dir() and not path.is_symlink(), 'media header component is not local: '+name)
    outer = view.entries(origin/name, {'include'})
    view.require({p.name for p in path.iterdir()} == set(outer) | {'include'}, 'media header component entries changed: '+name)
    for entry, item in outer.items():
        link = path/entry
        view.require(link.is_symlink() and os.readlink(link) == str(item), 'media integration link changed: '+str(link))
    projection.validate_projection(sourceprep, path/'include', package='electron-view/header-'+name,
                                   identity={'installed_package': ident})


def verify_view(view, source, destination, selected, sourceprep):
    origin = Path(source).resolve(strict=True)/'third_party'
    root = Path(destination).resolve(strict=True)/'src/third_party'
    view.require(set(selected) == set(NAMES), 'incomplete common media header selection')
    for name in NAMES:
        component(view, origin, root/name, name, selected[name], sourceprep)
    return Path(destination)/'src'


def activate(view, source, destination, selected, inventory, sourceprep, verify_old_whole, *, old_identities=None):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    origin, root = source/'third_party', destination/'src/third_party'
    identities = {name: identity(selected, name) for name in NAMES}
    view.require(old_identities is None or set(old_identities) == set(NAMES), 'partial old media header selection')
    names = list(NAMES) if old_identities is None else [n for n in NAMES if old_identities[n] != identities[n]]
    marker = destination.parent/('.'+destination.name+'.media-header-components-migration')
    if not names:
        view.require(not os.path.lexists(marker), 'unexpected media migration marker for unchanged selection')
        return verify_view(view, source, destination, identities, sourceprep)
    choice = hashlib.sha256(json.dumps({'old': old_identities, 'new': identities}, sort_keys=True).encode()).hexdigest()
    def check_old(path, name, partial):
        if old_identities is None:
            return path.is_symlink() and os.readlink(path) == str(origin/name)
        if partial:
            return path.is_dir() and not path.is_symlink()
        component(view, origin, path, name, old_identities[name], sourceprep)
        return True
    def build(name, path):
        path.mkdir()
        for entry, item in view.entries(origin/name, {'include'}).items():
            (path/entry).symlink_to(item, target_is_directory=item.is_dir())
        files = selected[name]['target']['header_files']
        if name == 'libyuv':
            mapped = {str(Path(key).relative_to('include')): val for key,val in files.items()}
        else:
            key = 'include/srtp2/srtp.h'
            view.require(key in files, 'missing installed public SRTP header')
            mapped = {'srtp.h': files[key]}
        previous = (root if old_identities is not None else origin)/name/'include'
        projection.prepare_selected_projection(inventory, previous, mapped, path/'include',
            sourceprep=sourceprep, package='electron-view/header-'+name,
            identity={'installed_package': identities[name]})
    def verify_new(migration):
        return verify_view(view, source, destination, identities, sourceprep)
    return view.sibling_component_transaction(destination, origin, names, choice, 'media-header-components',
        verify_old_whole, build, verify_new, check_old_entry=check_old,
        already_new=lambda: old_identities is None and all((root/n).is_dir() and not (root/n).is_symlink() for n in NAMES))
