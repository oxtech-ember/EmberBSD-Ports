# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Transactional projection of selected common ML source trees."""
import hashlib
import importlib.util
import json
import os
import stat
from pathlib import Path

_spec = importlib.util.spec_from_file_location('electron_ml_projection', Path(__file__).with_name('ml-source-projection.py'))
projection = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(projection)

COMPONENTS = {'ruy': 'ruy', 'pthreadpool': 'pthreadpool', 'gemmlowp': 'gemmlowp',
              'farmhash': 'farmhash', 'ml_dtypes': 'ml-dtypes', 'neon_2_sse': 'neon2sse',
              'fxdiv': 'fxdiv', 'fft2d': 'fft2d', 'litert': 'litert'}
NAMES = tuple(COMPONENTS) + ('tflite',)
ALIASES = (('tensorflow/lite', 'litert/src/tflite'), ('third_party/fft2d', 'fft2d/src'))


def receipt_identity(identities, name, subtree='.'):
    return {'common_tree_sha256': identities[name], 'subtree': subtree}


def verify_component(view, origin, selected, name, path, identities, sourceprep, *, legacy_root=None):
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
    for relative, target in ALIASES:
        link = src / relative
        expected = os.path.relpath(selected / target, (selected / 'tflite/src' / relative).parent)
        allowed = {expected}
        if legacy_root is not None:
            allowed.add(str(Path(legacy_root) / 'src/third_party' / target))
        view.require(link.is_symlink() and os.readlink(link) in allowed, 'ML alias changed: '+str(link))
    projection.validate_projection(sourceprep, src/'third_party/xla', package='electron-view/openxla',
        identity=receipt_identity(identities, 'openxla'))


def verify_view(view, source, destination, identities, sourceprep, *, legacy_root=None):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    origin, selected = source/'third_party', destination/'src/third_party'
    for name in NAMES:
        verify_component(view, origin, selected, name, selected/name, identities, sourceprep, legacy_root=legacy_root)
    return destination/'src'



def migrate_aliases(view, destination, legacy_root):
    """Replace preverified legacy aliases; temporary entries stay outside the view."""
    destination, legacy_root = Path(destination), Path(legacy_root)
    view.require(destination.is_absolute() and legacy_root.is_absolute(), 'invalid ML recovery roots')
    selected = destination / 'src/third_party'
    workfd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for index, (relative, target) in enumerate(ALIASES):
            parts = ('src', 'third_party', 'tflite', 'src', *Path(relative).parts)
            fd = os.open(destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=workfd)
            try:
                for part in parts[:-1]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd); fd = child
                name = parts[-1]
                before = os.stat(name, dir_fd=fd, follow_symlinks=False)
                current = os.readlink(name, dir_fd=fd)
                canonical = os.path.relpath(selected / target, (destination.joinpath(*parts)).parent)
                legacy = str(legacy_root / 'src/third_party' / target)
                view.require(stat.S_ISLNK(before.st_mode) and current in (canonical, legacy), 'foreign ML recovery alias')
                temp = '.ml-alias-' + destination.name + '-' + str(index)
                try:
                    info = os.stat(temp, dir_fd=workfd, follow_symlinks=False)
                except FileNotFoundError:
                    info = None
                if info is not None:
                    view.require(stat.S_ISLNK(info.st_mode) and os.readlink(temp, dir_fd=workfd) == canonical,
                                 'foreign ML recovery temporary entry')
                if current == canonical:
                    if info is not None:
                        again = os.stat(temp, dir_fd=workfd, follow_symlinks=False)
                        view.require((again.st_dev, again.st_ino, again.st_ctime_ns) ==
                                     (info.st_dev, info.st_ino, info.st_ctime_ns) and
                                     os.readlink(temp, dir_fd=workfd) == canonical,
                                     'ML recovery temporary entry changed')
                        os.unlink(temp, dir_fd=workfd); os.fsync(workfd)
                    continue
                if info is None:
                    os.symlink(canonical, temp, dir_fd=workfd); os.fsync(workfd)
                    info = os.stat(temp, dir_fd=workfd, follow_symlinks=False)
                parent_info = os.fstat(fd)
                live_parent = os.stat(destination.joinpath(*parts[:-1]), follow_symlinks=False)
                view.require((parent_info.st_dev, parent_info.st_ino) == (live_parent.st_dev, live_parent.st_ino),
                             'ML recovery parent changed')
                now = os.stat(name, dir_fd=fd, follow_symlinks=False)
                view.require((now.st_dev, now.st_ino, now.st_mode, now.st_ctime_ns) ==
                             (before.st_dev, before.st_ino, before.st_mode, before.st_ctime_ns) and
                             os.readlink(name, dir_fd=fd) == current, 'ML recovery alias changed')
                staged = os.stat(temp, dir_fd=workfd, follow_symlinks=False)
                view.require(stat.S_ISLNK(staged.st_mode) and os.readlink(temp, dir_fd=workfd) == canonical,
                             'ML recovery temporary entry changed')
                view.require((staged.st_dev, staged.st_ino, staged.st_ctime_ns) ==
                             (info.st_dev, info.st_ino, info.st_ctime_ns),
                             'ML recovery temporary entry replaced')
                os.replace(temp, name, src_dir_fd=workfd, dst_dir_fd=fd)
                os.fsync(fd); os.fsync(workfd)
            finally:
                os.close(fd)
    finally:
        os.close(workfd)


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
            (src/'tensorflow/lite').symlink_to(os.path.relpath(selected/'litert/src/tflite', selected/'tflite/src/tensorflow'), target_is_directory=True)
            (src/'third_party/fft2d').symlink_to(os.path.relpath(selected/'fft2d/src', selected/'tflite/src/third_party'), target_is_directory=True)
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
