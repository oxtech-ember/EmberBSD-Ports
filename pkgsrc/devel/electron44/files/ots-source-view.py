# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Project verified common OpenType Sanitizer source under Chromium's GN glue."""
import hashlib
import json
import os
from pathlib import Path

NAME = 'ots'
PACKAGE = 'fonts/opentype-sanitizer'


def selection(view, sourceprep, source):
    original = Path(source)
    view.require(original.is_absolute() and original.is_dir() and not original.is_symlink(),
                 'invalid OpenType Sanitizer source directory')
    root = original.resolve(strict=True)
    receipt = sourceprep.read_prepared_tree_receipt(str(root), package=PACKAGE)
    sourceprep.validate_prepared_tree(str(root), package=PACKAGE, identity=receipt['identity'])
    record_path = root / sourceprep.PREPARED_TREE_RECEIPT
    def stable(st):
        return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    before = stable(record_path.stat()); raw = record_path.read_bytes()
    view.require(stable(record_path.stat()) == before, 'OpenType Sanitizer receipt changed during verification')
    return {'path': str(root), 'tree_sha256': receipt['tree_sha256'],
            'receipt_sha256': hashlib.sha256(raw).hexdigest()}


def component(view, origin, path, selected):
    view.dependency_view(origin / NAME, path, {Path('src'): Path(selected['path'])}, set(), verify=True)


def verify_view(view, source, destination, selected, sourceprep):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    view.require(selection(view, sourceprep, selected['path']) == selected,
                 'OpenType Sanitizer selection changed')
    component(view, source / 'third_party', destination / 'src/third_party' / NAME, selected)
    return destination / 'src'


def activate(view, source, destination, selected, old, sourceprep, verify_old):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    origin = source / 'third_party'
    marker = destination.parent / ('.' + destination.name + '.ots-components-migration')
    if old == selected:
        view.require(not os.path.lexists(marker), 'unexpected OpenType Sanitizer migration marker')
        return verify_view(view, source, destination, selected, sourceprep)
    identity = hashlib.sha256(json.dumps({'old': old, 'new': selected}, sort_keys=True).encode()).hexdigest()

    def check_old(path, name, partial):
        if old is None:
            return path.is_symlink() and os.readlink(path) == str(origin / name)
        if partial:
            return path.is_dir() and not path.is_symlink()
        component(view, origin, path, old)
        return True

    def build(name, path):
        view.dependency_view(origin / name, path, {Path('src'): Path(selected['path'])}, set())

    return view.sibling_component_transaction(
        destination, origin, [NAME], identity, 'ots-components', verify_old, build,
        lambda _: verify_view(view, source, destination, selected, sourceprep),
        check_old_entry=check_old, already_new=lambda: False)
