#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Allow only a first verified provider addition, never replacement."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',p); e=importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
o=SimpleNamespace(shared_pdf_libraries=True)
keys={'emberbsd_'+p+'_'+r+'_'+k for p in ('lcms2','openjpeg','tiff') for r in ('host','target') for k in ('libraries','inputs')}
keys.update(('emberbsd_common_pdf','use_system_lcms2','use_system_libopenjpeg2','use_system_libtiff'))
values={key:True if key in ('emberbsd_common_pdf','use_system_lcms2','use_system_libopenjpeg2','use_system_libtiff') else ['/verified/'+key] for key in keys}; env={'EMBERBSD_PDF_SOURCE_SHA256':'a'*64}
assert e.pdfium_activation_args(o,{},env,{},values)==keys
assert e.pdfium_activation_args(o,env,env,values,values)==set()
for old,new in (({next(iter(keys)):['/foreign']},values), ({}, {**values, next(iter(keys)):[]})):
    try: e.pdfium_activation_args(o,{},env,old,new)
    except ValueError: pass
    else: raise AssertionError('unverified replacement or incomplete selection accepted')
# A changed previously selected argument is not exempt from the normal identity check.
changed={**values, 'emberbsd_lcms2_host_libraries':['/other']}
allowed=e.pdfium_activation_args(o,env,env,values,changed)
assert not allowed and any(values[k]!=changed[k] for k in keys)
print('PASS: first PDFium activation is additive; later changes remain guarded')
