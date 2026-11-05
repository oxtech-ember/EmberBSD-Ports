# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Project the verified Chromium recovery amalgamation into its existing wrapper."""
import hashlib
import json
import os
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
    before = receipt.stat(); raw = receipt.read_bytes()
    view.require(receipt.stat() == before, 'SQLite receipt changed during verification')
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
        before = path.stat(); file_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        view.require(path.stat() == before and file_digest == data['files'][name],
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


def component(view, origin, path, selected):
    repl = replacements(selected)
    view.dependency_view(origin / NAME, path, repl, set(), verify=True)


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
    identity = hashlib.sha256(json.dumps({'old': old, 'new': selected}, sort_keys=True).encode()).hexdigest()
    def check_old(path, name, partial):
        if old is None:
            return path.is_symlink() and os.readlink(path) == str(origin / name)
        if partial:
            return path.is_dir() and not path.is_symlink()
        component(view, origin, path, old)
        return True
    def build(name, path):
        view.dependency_view(origin / name, path, replacements(selected), set())
    return view.sibling_component_transaction(
        destination, origin, [NAME], identity, 'sqlite-components', verify_old, build,
        lambda _: verify_view(view, source, destination, selected),
        check_old_entry=check_old, already_new=lambda: False)
