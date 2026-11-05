# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Transactional projection of selected common ML source trees."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

_spec = importlib.util.spec_from_file_location('electron_ml_projection', Path(__file__).with_name('ml-source-projection.py'))
projection = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(projection)

COMPONENTS = {'ruy': 'ruy', 'pthreadpool': 'pthreadpool', 'gemmlowp': 'gemmlowp',
              'farmhash': 'farmhash', 'ml_dtypes': 'ml-dtypes', 'neon_2_sse': 'neon2sse',
              'fxdiv': 'fxdiv', 'fft2d': 'fft2d', 'litert': 'litert'}
NAMES = tuple(COMPONENTS) + ('tflite',)


def receipt_identity(identities, name, subtree='.'):
    return {'common_tree_sha256': identities[name], 'subtree': subtree}


def verify_component(view, origin, selected, name, path, identities, sourceprep):
    view.require(path.is_dir() and not path.is_symlink(), 'ML view component is not local: '+name)
    outer = view.entries(origin/name, {'src'})
    view.require({p.name for p in path.iterdir()} == set(outer) | {'src'}, 'ML component entries changed: '+name)
    for entry, item in outer.items():
        link = path/entry
        view.require(link.is_symlink() and os.readlink(link) == str(item), 'ML integration link changed: '+str(link))
    if name != 'tflite':
        provider = COMPONENTS[name]
        projection.validate_projection(sourceprep, path/'src', package='electron-view/'+provider,
            identity=receipt_identity(identities, provider))
        return
    src = path/'src'
    view.require({p.name for p in src.iterdir()} == {'tensorflow', 'third_party'} and
                 {p.name for p in (src/'tensorflow').iterdir()} == {'lite'} and
                 {p.name for p in (src/'third_party').iterdir()} == {'xla', 'fft2d'},
                 'TFLite common source view changed')
    for link, target in ((src/'tensorflow/lite', selected/'litert/src/tflite'),
                         (src/'third_party/fft2d', selected/'fft2d/src')):
        view.require(link.is_symlink() and os.readlink(link) == str(target), 'ML alias changed: '+str(link))
    projection.validate_projection(sourceprep, src/'third_party/xla', package='electron-view/openxla',
        identity=receipt_identity(identities, 'openxla'))


def verify_view(view, source, destination, identities, sourceprep):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    origin, selected = source/'third_party', destination/'src/third_party'
    for name in NAMES:
        verify_component(view, origin, selected, name, selected/name, identities, sourceprep)
    return destination/'src'


def activate(view, source, destination, providers, identities, inventory, sourceprep, verify_old_whole, *, old_identities=None):
    """Activate verified providers; caller holds locks and GN-incomplete guard."""
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    origin, selected = source/'third_party', destination/'src/third_party'
    expected = set(COMPONENTS.values()) | {'openxla'}
    view.require(set(providers) == set(identities) == expected, 'incomplete ML source selection')
    providers = {name: Path(path).resolve(strict=True) for name, path in providers.items()}
    for digest in identities.values():
        view.require(isinstance(digest, str) and len(digest) == 64 and all(c in '0123456789abcdef' for c in digest),
                     'invalid ML source identity')
    marker = destination.parent / ('.' + destination.name + '.ml-components-migration')
    if old_identities is not None and not os.path.lexists(marker):
        try:
            return verify_view(view, source, destination, identities, sourceprep)
        except Exception:
            pass  # The old verified selection may need an incremental transition.
    if old_identities is not None:
        view.require(set(old_identities) == expected, 'incomplete old ML selection')
        names = [name for name, provider in COMPONENTS.items() if old_identities[provider] != identities[provider]]
        if old_identities['openxla'] != identities['openxla']:
            names.append('tflite')
        if not names:
            return verify_view(view, source, destination, identities, sourceprep)
    else:
        names = list(NAMES)
    choice = hashlib.sha256(json.dumps({'old': old_identities, 'new': identities}, sort_keys=True).encode()).hexdigest()
    def check_old(path, name, partial):
        if old_identities is None:
            return path.is_symlink() and os.readlink(path) == str(origin/name)
        if partial:
            return path.is_dir() and not path.is_symlink()
        verify_component(view, origin, selected, name, path, old_identities, sourceprep)
        return True


    def build(name, path):
        path.mkdir()
        for entry, item in view.entries(origin/name, {'src'}).items():
            (path/entry).symlink_to(item, target_is_directory=item.is_dir())
        if name == 'tflite':
            src = path/'src'; (src/'tensorflow').mkdir(parents=True); (src/'third_party').mkdir()
            (src/'tensorflow/lite').symlink_to(selected/'litert/src/tflite', target_is_directory=True)
            (src/'third_party/fft2d').symlink_to(selected/'fft2d/src', target_is_directory=True)
            old_xla = (selected if old_identities is not None else origin)/'tflite/src/third_party/xla'
            projection.prepare_projection(inventory, old_xla, providers['openxla'],
                src/'third_party/xla', sourceprep=sourceprep, package='electron-view/openxla',
                identity=receipt_identity(identities, 'openxla'))
            return
        provider = COMPONENTS[name]
        previous = selected if old_identities is not None else origin
        aliases = []
        if name == 'litert':
            aliases.append(('tflite', previous/'tflite/src/tensorflow/lite'))
        elif name == 'fft2d':
            aliases.append(('.', previous/'tflite/src/third_party/fft2d'))
        projection.prepare_projection(inventory, previous/name/'src', providers[provider], path/'src',
            old_aliases=aliases, sourceprep=sourceprep, package='electron-view/'+provider,
            identity=receipt_identity(identities, provider))

    def verify_new(migration):
        return verify_view(view, source, destination, identities, sourceprep)

    return view.sibling_component_transaction(destination, origin, names, choice, 'ml-components',
        verify_old_whole, build, verify_new, check_old_entry=check_old,
        already_new=lambda: old_identities is None and all((selected/name).is_dir() and not (selected/name).is_symlink() for name in NAMES))
