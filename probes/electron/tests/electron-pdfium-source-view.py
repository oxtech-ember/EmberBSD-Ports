#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Migrate PDFium's font-only projection and strictly recover a compound view."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import tempfile
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(n,p):
 s=importlib.util.spec_from_file_location(n,owner/p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
v=load('view','protobuf-source-view.py');f=load('font','font-table-view.py')
with tempfile.TemporaryDirectory() as tmp:
 r=Path(tmp).resolve();source=r/'source';origin=source/'third_party';pdf=origin/'pdfium';dest=r/'view';selected=dest/'src/third_party'
 (pdf/'third_party/freetype/include').mkdir(parents=True);(pdf/'third_party/freetype/include/pstables.h').write_text('bundled')
 for n in ('lcms','libopenjpeg','libtiff'):
  (pdf/'third_party'/n).mkdir(parents=True);(pdf/'third_party'/n/'vendor.h').write_text('bundled')
 (pdf/'core').mkdir();(pdf/'core/unchanged').write_text('unchanged');(origin/'neighbor').mkdir()
 selected.mkdir(parents=True);(selected/'pdfium').symlink_to(pdf,target_is_directory=True);(selected/'neighbor').symlink_to(origin/'neighbor')
 table=r/'pstables.h';table.write_text('selected')
 with patch.object(f,'verify_view',side_effect=ValueError('legacy interrupted')):
  try:f.activate(v,source,dest,table,lambda:None)
  except ValueError:pass
  else:raise AssertionError('interrupted legacy transaction accepted')
 assert (r/'.view.font-table-components-migration').is_file()
 f.activate(v,source,dest,table,lambda:None)
 assert not (r/'.view.font-table-components-migration').exists()
 core=selected/'pdfium/core';before=(core.lstat().st_mtime_ns,(core/'unchanged').stat().st_mtime_ns);neighbor=(selected/'neighbor').lstat().st_ino
 def old():f.verify_view(v,source,dest,table)
 with patch.object(f,'verify_pdfium',side_effect=ValueError('interrupted')):
  try:f.activate_pdfium(v,source,dest,table,False,table,True,old)
  except ValueError:pass
  else:raise AssertionError('interrupted transaction accepted')
 assert (r/'.view.pdfium-components-migration').is_file()
 f.activate_pdfium(v,source,dest,table,False,table,True,old)
 f.verify_pdfium(v,source,dest,table,True)
 assert not (r/'.view.pdfium-components-migration').exists()
 assert (core.lstat().st_mtime_ns,(core/'unchanged').stat().st_mtime_ns)==before
 assert (selected/'neighbor').lstat().st_ino==neighbor
 assert (selected/'pdfium/third_party/freetype/include/pstables.h').read_text()=='selected'
 for n in ('lcms','libopenjpeg','libtiff'):assert not (selected/'pdfium/third_party'/n).exists()
 f.activate_pdfium(v,source,dest,table,True,table,True,lambda:(_ for _ in ()).throw(AssertionError('unexpected replacement')))
 (selected/'pdfium/core').unlink();(selected/'pdfium/core').symlink_to(r/'foreign')
 try:f.verify_pdfium(v,source,dest,table,True)
 except ValueError:pass
 else:raise AssertionError('foreign projection accepted')
# Independent opt-in works when the shared FreeType table is not selected.
with tempfile.TemporaryDirectory() as tmp:
 r=Path(tmp).resolve();source=r/'source';pdf=source/'third_party/pdfium';dest=r/'view';selected=dest/'src/third_party'
 (pdf/'third_party/freetype/include').mkdir(parents=True);(pdf/'third_party/freetype/include/pstables.h').write_text('bundled')
 for name in ('lcms','libopenjpeg','libtiff'):
  (pdf/'third_party'/name).mkdir(parents=True);(pdf/'third_party'/name/'vendor.h').write_text('bundled')
 selected.mkdir(parents=True);(selected/'pdfium').symlink_to(pdf,target_is_directory=True)
 f.activate_pdfium(v,source,dest,None,False,None,True,lambda:None)
 f.verify_pdfium(v,source,dest,None,True)
 assert (selected/'pdfium/third_party/freetype/include/pstables.h').read_text()=='bundled'
 for name in ('lcms','libopenjpeg','libtiff'):assert not (selected/'pdfium/third_party'/name).exists()
# A fresh font + PDF selection is one transaction from the original symlink.
with tempfile.TemporaryDirectory() as tmp:
 r=Path(tmp).resolve();source=r/'source';pdf=source/'third_party/pdfium';dest=r/'view';selected=dest/'src/third_party'
 (pdf/'third_party/freetype/include').mkdir(parents=True);(pdf/'third_party/freetype/include/pstables.h').write_text('bundled')
 for name in ('lcms','libopenjpeg','libtiff'):(pdf/'third_party'/name).mkdir(parents=True)
 selected.mkdir(parents=True);(selected/'pdfium').symlink_to(pdf,target_is_directory=True)
 table=r/'pstables.h';table.write_text('selected')
 f.activate_pdfium(v,source,dest,None,False,table,True,lambda:None)
 f.verify_pdfium(v,source,dest,table,True)
 assert (selected/'pdfium/third_party/freetype/include/pstables.h').read_text()=='selected'
 for name in ('lcms','libopenjpeg','libtiff'):assert not (selected/'pdfium/third_party'/name).exists()
print('PASS: PDFium font migration, shared masks, mtime, retry and foreign rejection')
