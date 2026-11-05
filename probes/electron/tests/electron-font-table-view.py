#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Project only the selected owned FreeType table, with safe retry."""
import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch

owner = Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name, file):
    spec=importlib.util.spec_from_file_location(name,owner/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
view=load('view','protobuf-source-view.py');font=load('font','font-table-view.py')
with tempfile.TemporaryDirectory(prefix='electron-font-table-') as tmp:
    root=Path(tmp).resolve();source=root/'source';origin=source/'third_party';origin.mkdir(parents=True)
    pdf=origin/'pdfium';(pdf/'third_party/freetype/include').mkdir(parents=True)
    (pdf/'third_party/freetype/include/pstables.h').write_text('old table')
    (pdf/'BUILD.gn').write_text('pdfium build')
    (pdf/'core').mkdir();(pdf/'core/file').write_text('unchanged')
    (origin/'neighbor').mkdir();(origin/'neighbor/file').write_text('neighbor')
    dest=root/'view';selected=dest/'src/third_party';selected.mkdir(parents=True)
    (selected/'pdfium').symlink_to(pdf,target_is_directory=True)
    (selected/'neighbor').symlink_to(origin/'neighbor',target_is_directory=True)
    table=root/'prefix/share/freetype2/generated/pstables.h';table.parent.mkdir(parents=True);table.write_text('selected table')
    neighbor=(selected/'neighbor').lstat();core_time=(selected/'pdfium/core/file').stat().st_mtime_ns
    def old():
        assert (selected/'pdfium').is_symlink()
    with patch.object(font, 'verify_view', side_effect=ValueError('interrupted')):
        try:font.activate(view,source,dest,table,old)
        except ValueError:pass
        else:raise AssertionError('interrupted projection was accepted')
    assert (root/'.view.font-table-components-migration').is_file()
    font.activate(view,source,dest,table,old)
    assert not (root/'.view.font-table-components-migration').exists()
    assert (selected/'pdfium/third_party/freetype/include/pstables.h').read_text()=='selected table'
    assert (selected/'pdfium/core/file').stat().st_mtime_ns==core_time
    assert (selected/'neighbor').lstat().st_ino==neighbor.st_ino
    font.verify_view(view,source,dest,table)
    font.activate(view,source,dest,table,old)
    link=selected/'pdfium/third_party/freetype/include/pstables.h';link.unlink();link.symlink_to(pdf/'third_party/freetype/include/pstables.h')
    try:font.verify_view(view,source,dest,table)
    except ValueError:pass
    else:raise AssertionError('foreign table accepted')
print('PASS: owned PDFium table projection, sibling preservation and retry')
