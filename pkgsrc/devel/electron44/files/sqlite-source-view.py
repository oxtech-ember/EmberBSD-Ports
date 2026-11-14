# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Project the verified Chromium recovery amalgamation into its existing wrapper."""
import hashlib
import json
import os
import re
from pathlib import Path

NAME = 'sqlite'
FILES = ('sqlite3.c', 'sqlite3.h', 'rename_exports.h', 'shell/shell.c',
         'dev/sqlite3.c', 'dev/sqlite3.h', 'dev/rename_exports.h', 'dev/shell/shell.c')


def selection(view, output):
    original = Path(output)
    view.require(original.is_absolute() and original.is_dir() and not original.is_symlink(),
                 'invalid SQLite amalgamation directory')
    root = original.resolve(strict=True)
    receipt = root / 'receipt.json'
    view.require(receipt.is_file() and not receipt.is_symlink(), 'invalid SQLite receipt')
    from emberbsd_sdk import paths
    stream, before = paths.open_regular(receipt)
    with stream:
        raw = stream.read()
        view.require(paths.stable_identity(os.fstat(stream.fileno())) == paths.stable_identity(before),
                     'SQLite receipt changed during verification')
    paths.verify_stable(receipt, before)
    receipt_digest = hashlib.sha256(raw).hexdigest()
    view.require(root.name == 'amalgamation-' + receipt_digest, 'SQLite receipt identity mismatch')
    data = json.loads(raw)
    view.require(isinstance(data, dict) and data.get('format') == 'emberbsd-chromium-sqlite' and
                 data.get('version') == 1 and isinstance(data.get('identity'), dict) and
                 isinstance(data.get('files'), dict) and set(data['files']) == set(FILES),
                 'invalid SQLite amalgamation receipt')
    for name in FILES:
        path = root / name
        view.require(path.is_file() and not path.is_symlink(), 'invalid SQLite amalgamation file: ' + name)
        stream, before = paths.open_regular(path)
        with stream:
            file_digest = hashlib.sha256(stream.read()).hexdigest()
            view.require(paths.stable_identity(os.fstat(stream.fileno())) == paths.stable_identity(before),
                         'SQLite file changed during verification: ' + name)
        paths.verify_stable(path, before)
        view.require(file_digest == data['files'][name],
                     'SQLite amalgamation file differs from receipt: ' + name)
    source = data['identity'].get('source')
    view.require(isinstance(source, str) and Path(source).is_absolute() and
                 (Path(source)/'test').is_dir(), 'invalid SQLite common test source')
    return {'path': str(root), 'source': source, 'receipt': receipt_digest}, data


def replacements(selected):
    result = {(Path('src/amalgamation_dev') / name[4:] if name.startswith('dev/')
               else Path('src/amalgamation') / name): Path(selected['path']) / name for name in FILES}
    result[Path('src/test')] = Path(selected['source']) / 'test'
    return result


def component(view, origin, path, selected, *, partial=False):
    repl = replacements(selected)
    view.dependency_view(origin / NAME, path, repl, set(), verify=True, partial=partial)


def validate_retired_selection(view, selected):
    view.require(isinstance(selected, dict) and set(selected) == {'path', 'source', 'receipt'},
                 'invalid retired SQLite selection')
    digest = selected['receipt']
    view.require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest),
                 'invalid retired SQLite receipt identity')
    for key in ('path', 'source'):
        value = selected[key]
        view.require(isinstance(value, str) and os.path.isabs(value) and os.path.normpath(value) == value,
                     'invalid retired SQLite ' + key)
    view.require(Path(selected['path']).name == 'amalgamation-' + digest,
                 'invalid retired SQLite amalgamation identity')


def verify_retired_view(view, source, destination, selected):
    validate_retired_selection(view, selected)
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    component(view, source / 'third_party', destination / 'src/third_party' / NAME, selected)
    return destination / 'src'


def verify_view(view, source, destination, selected):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    actual, _ = selection(view, selected['path'])
    view.require(actual == selected, 'SQLite selection changed')
    component(view, source / 'third_party', destination / 'src/third_party' / NAME, selected)
    return destination / 'src'


def activate(view, source, destination, selected, old, verify_old):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    origin, root = source / 'third_party', destination / 'src/third_party'
    marker = destination.parent / ('.' + destination.name + '.sqlite-components-migration')
    if old == selected:
        view.require(not os.path.lexists(marker), 'unexpected SQLite migration marker')
        return verify_view(view, source, destination, selected)
    if old is not None:
        validate_retired_selection(view, old)
    identity = hashlib.sha256(json.dumps({'old': old, 'new': selected}, sort_keys=True).encode()).hexdigest()
    def check_old(path, name, partial):
        if old is None:
            return path.is_symlink() and os.readlink(path) == str(origin / name)
        component(view, origin, path, old, partial=partial)
        return True
    def build(name, path):
        view.dependency_view(origin / name, path, replacements(selected), set())
    return view.sibling_component_transaction(
        destination, origin, [NAME], identity, 'sqlite-components', verify_old, build,
        lambda _: verify_view(view, source, destination, selected),
        check_old_entry=check_old, already_new=lambda: False)


def recover_equivalent_initial(view, source, destination, selected):
    """Recover an initial projection only when all generated inputs match."""
    marker = Path(destination).parent / ('.' + Path(destination).name + '.sqlite-components-migration')
    view.require(not os.path.lexists(marker), 'pending SQLite migration requires transaction recovery')
    link = Path(destination) / 'src/third_party/sqlite/src/amalgamation/sqlite3.c'
    view.require(link.is_symlink(), 'initial SQLite projection has no selected amalgamation')
    target = Path(os.readlink(link))
    view.require(target.is_absolute() and target.name == 'sqlite3.c', 'invalid initial SQLite target')
    old, old_receipt = selection(view, target.parent)
    current, new_receipt = selection(view, selected['path'])
    view.require(current == selected, 'new SQLite selection changed')
    old_identity = dict(old_receipt['identity']); new_identity = dict(new_receipt['identity'])
    old_generator = old_identity.pop('generator_sha256', None)
    new_generator = new_identity.pop('generator_sha256', None)
    view.require(isinstance(old_generator, str) and re.fullmatch(r'[0-9a-f]{64}', old_generator) and
                 isinstance(new_generator, str) and re.fullmatch(r'[0-9a-f]{64}', new_generator) and
                 old_identity == new_identity and old_receipt['files'] == new_receipt['files'],
                 'initial SQLite projection differs from current generated inputs')
    verify_view(view, source, destination, old)
    return old
