# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Project the package-owned FreeType generated table into PDFium's source view."""
import hashlib
from pathlib import Path

NAME = 'pdfium'
TABLE = Path('third_party/freetype/include/pstables.h')


def verify_view(view, source, destination, table):
    origin = Path(source).resolve(strict=True) / 'third_party' / NAME
    selected = Path(destination).resolve(strict=True) / 'src/third_party' / NAME
    table = Path(table).resolve(strict=True)
    view.require(table.is_file(), 'selected FreeType generated table is missing')
    view.dependency_view(origin, selected, {TABLE: table}, set(), verify=True)
    return Path(destination) / 'src'


def activate(view, source, destination, table, verify_old_whole):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve(strict=True)
    origin = source / 'third_party'
    selected = destination / 'src/third_party'
    table = Path(table).resolve(strict=True)
    view.require(table.is_file(), 'selected FreeType generated table is missing')
    identity = hashlib.sha256(str(table).encode() + b'\0' + table.read_bytes()).hexdigest()
    def build(name, path):
        view.dependency_view(origin/name, path, {TABLE: table}, set())
    return view.sibling_component_transaction(
        destination, origin, [NAME], identity, 'font-table-components',
        verify_old_whole, build, lambda _: verify_view(view, source, destination, table),
        already_new=lambda: (selected/NAME).is_dir() and not (selected/NAME).is_symlink())

# One PDFium sibling owns both the FreeType table and common image-library
# exclusions; selecting either feature must preserve the other.
PDF_MASKS = frozenset(Path('third_party') / name for name in ('lcms', 'libopenjpeg', 'libtiff'))


def pdfium_selection(table, shared):
    table = Path(table).resolve(strict=True) if table is not None else None
    return table, bool(shared)


def verify_pdfium(view, source, destination, table, shared):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve(strict=True)
    table, shared = pdfium_selection(table, shared)
    replacements = {TABLE: table} if table is not None else {}
    masks = PDF_MASKS if shared else set()
    view.dependency_view(source/'third_party'/NAME, destination/'src/third_party'/NAME,
                         replacements, masks, verify=True)
    return destination/'src'


def activate_pdfium(view, source, destination, old_table, old_shared, table, shared, verify_old_whole):
    """Migrate the PDFium sibling without replacing the old font-only journal."""
    import json
    import os
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve(strict=True)
    origin = source/'third_party'; selected = destination/'src/third_party'
    old_table, old_shared = pdfium_selection(old_table, old_shared)
    table, shared = pdfium_selection(table, shared)
    def spec(value, use_shared):
        return {'table': str(value) if value is not None else None,
                'table_sha256': hashlib.sha256(value.read_bytes()).hexdigest() if value is not None else None,
                'shared': use_shared}
    identity = hashlib.sha256(json.dumps({'old': spec(old_table, old_shared), 'new': spec(table, shared)},
                                         sort_keys=True).encode()).hexdigest()
    def valid(path, selected_table, use_shared):
        replacements = {TABLE: selected_table} if selected_table is not None else {}
        masks = PDF_MASKS if use_shared else set()
        view.dependency_view(origin/NAME, path, replacements, masks, verify=True)
    def old_entry(path, name, partial):
        if old_table is None and not old_shared:
            return path.is_symlink() and os.readlink(path) == str(origin/name)
        if partial:
            return path.is_dir() and not path.is_symlink()
        valid(path, old_table, old_shared)
        return True
    def already_new():
        try:
            valid(selected/NAME, table, shared)
        except (ValueError, OSError):
            return False
        return True
    def build(name, path):
        replacements = {TABLE: table} if table is not None else {}
        view.dependency_view(origin/name, path, replacements, PDF_MASKS if shared else set())
        # Keep the mtimes of unchanged symlink leaves; the whole old view was
        # verified before staging and each link is checked again before reuse.
        old_root = selected/name
        if old_root.is_dir() and not old_root.is_symlink():
            for parent, dirs, files in os.walk(path, followlinks=False):
                for entry in dirs + files:
                    new = Path(parent)/entry
                    old = old_root/new.relative_to(path)
                    if new.is_symlink() and old.is_symlink() and os.readlink(new) == os.readlink(old):
                        before = os.lstat(old)
                        os.utime(new, ns=(before.st_atime_ns, before.st_mtime_ns), follow_symlinks=False)
                        view.require(os.lstat(old) == before, 'old PDFium link changed during staging')
    return view.sibling_component_transaction(
        destination, origin, [NAME], identity, 'pdfium-components', verify_old_whole, build,
        lambda _: verify_pdfium(view, source, destination, table, shared),
        check_old_entry=old_entry, already_new=already_new)
