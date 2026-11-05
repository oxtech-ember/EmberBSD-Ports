# SPDX-License-Identifier: BSD-2-Clause
"""Project one verified common BoringSSL tree into Chromium's GN wrapper."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

_spec = importlib.util.spec_from_file_location('electron_boringssl_projection', Path(__file__).with_name('ml-source-projection.py'))
projection = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(projection)
NAME = 'boringssl'


def component(view, origin, path, digest, sourceprep):
    view.require(path.is_dir() and not path.is_symlink(), 'BoringSSL view is not local')
    outer = view.entries(origin/NAME, {'src'})
    view.require({p.name for p in path.iterdir()} == set(outer) | {'src'}, 'BoringSSL wrapper entries changed')
    for name, item in outer.items():
        link = path/name
        view.require(link.is_symlink() and os.readlink(link) == str(item), 'BoringSSL wrapper link changed: '+str(link))
    projection.validate_projection(sourceprep, path/'src', package='electron-view/boringssl',
                                   identity={'tree_sha256': digest})


def verify_view(view, source, destination, digest, sourceprep):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    component(view, source/'third_party', destination/'src/third_party'/NAME, digest, sourceprep)
    return destination/'src'


def activate(view, source, destination, provider, digest, inventory, sourceprep, verify_old_whole, *, old_digest=None):
    """Use the shared sibling transaction, keeping the surrounding view intact."""
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    provider = Path(provider).resolve(strict=True)
    view.require(len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), 'invalid BoringSSL source identity')
    origin, root = source/'third_party', destination/'src/third_party'
    marker = destination.parent/('.'+destination.name+'.boringssl-components-migration')
    if old_digest == digest:
        view.require(not os.path.lexists(marker), 'unexpected BoringSSL migration marker for unchanged selection')
        return verify_view(view, source, destination, digest, sourceprep)
    choice = hashlib.sha256(json.dumps({'old':old_digest,'new':digest}, sort_keys=True).encode()).hexdigest()
    def check_old(path, name, partial):
        if old_digest is None:
            return path.is_symlink() and os.readlink(path) == str(origin/name)
        if partial:
            return path.is_dir() and not path.is_symlink()
        component(view, origin, path, old_digest, sourceprep)
        return True
    def build(name, path):
        path.mkdir()
        for entry, item in view.entries(origin/name, {'src'}).items():
            (path/entry).symlink_to(item, target_is_directory=item.is_dir())
        previous = (root if old_digest is not None else origin)/name/'src'
        projection.prepare_projection(inventory, previous, provider, path/'src', sourceprep=sourceprep,
                                      package='electron-view/boringssl', identity={'tree_sha256':digest})
    def verify_new(migration):
        return verify_view(view, source, destination, digest, sourceprep)
    return view.sibling_component_transaction(destination, origin, [NAME], choice, 'boringssl-components',
        verify_old_whole, build, verify_new, check_old_entry=check_old,
        already_new=lambda: old_digest is None and (root/NAME).is_dir() and not (root/NAME).is_symlink())
