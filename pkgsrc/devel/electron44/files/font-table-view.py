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
