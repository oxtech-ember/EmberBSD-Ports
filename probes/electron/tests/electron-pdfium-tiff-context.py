#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run PDFium's actual TIFF diagnostic callback against the selected library."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p=argparse.ArgumentParser(description=__doc__)
for name in ('source','cc','include','library'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--cc-arg',action='append',default=[])
a=p.parse_args()
source=a.source.resolve(strict=True).read_text()
start=source.index('int QuietTiffDiagnostic(');end=source.index('\n}',start)+2
callback=source[start:end]
for required in ('TIFFOpenOptionsSetMaxCumulatedMemAlloc', 'TIFFOpenOptionsSetErrorHandlerExtR',
                 'TIFFOpenOptionsSetWarningHandlerExtR', 'TIFFClientOpenExt'):
    assert required in source, required
assert 'TIFFSetErrorHandler(' not in source and 'TIFFSetWarningHandler(' not in source
with tempfile.TemporaryDirectory(prefix='pdfium-tiff-context-') as temp:
    root=Path(temp);test=root/'test.cpp';binary=root/'test';fixture=root/'fixture.tif'
    test.write_text('''#include <tiffio.h>\n#include <cstdarg>\n'''+callback+'''\n
static int global_warnings=0, global_errors=0;
static void warning(const char*,const char*,va_list) { ++global_warnings; }
static void error(const char*,const char*,va_list) { ++global_errors; }
int main(int argc,char**argv) {
 if(argc!=2)return 1;
 TIFF* w=TIFFOpen(argv[1],"w"); if(!w)return 2;
 TIFFSetField(w,TIFFTAG_IMAGEWIDTH,1); TIFFSetField(w,TIFFTAG_IMAGELENGTH,1);
 TIFFSetField(w,TIFFTAG_BITSPERSAMPLE,8); TIFFSetField(w,TIFFTAG_SAMPLESPERPIXEL,1);
 TIFFSetField(w,TIFFTAG_ROWSPERSTRIP,1); TIFFSetField(w,TIFFTAG_PHOTOMETRIC,PHOTOMETRIC_MINISBLACK);
 unsigned char pixel=0; if(TIFFWriteScanline(w,&pixel,0,0)<0)return 3; TIFFClose(w);
 TIFFSetWarningHandler(warning); TIFFSetErrorHandler(error);
 TIFFOpenOptions* opts=TIFFOpenOptionsAlloc(); if(!opts)return 4;
 TIFFOpenOptionsSetWarningHandlerExtR(opts,QuietTiffDiagnostic,nullptr);
 TIFFOpenOptionsSetErrorHandlerExtR(opts,QuietTiffDiagnostic,nullptr);
 TIFF* quiet=TIFFOpenExt(argv[1],"r",opts); TIFFOpenOptionsFree(opts); if(!quiet)return 5;
 TIFFWarningExtR(quiet,"test","warning"); TIFFErrorExtR(quiet,"test","error"); TIFFClose(quiet);
 if(global_warnings || global_errors)return 6;
 TIFF* normal=TIFFOpen(argv[1],"r"); if(!normal)return 7;
 TIFFWarningExtR(normal,"test","warning"); TIFFErrorExtR(normal,"test","error"); TIFFClose(normal);
 return global_warnings==1 && global_errors==1 ? 0 : 8;
}\n''')
    command=[str(a.cc.resolve(strict=True)),*a.cc_arg,'-I'+str(a.include.resolve(strict=True)),str(test),
             str(a.library.resolve(strict=True)),'-Wl,-rpath,'+str(a.library.resolve().parent),'-o',str(binary)]
    subprocess.run(command,check=True,capture_output=True)
    subprocess.run([str(binary),str(fixture)],check=True,capture_output=True)
print('PASS: PDFium TIFF diagnostics are quiet per handle and preserve global handlers')
