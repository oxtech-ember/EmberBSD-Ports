#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise PDFium's actual LCMS allocator callbacks and context lifetime."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p=argparse.ArgumentParser(description=__doc__)
for name in ('source','cc','include','library'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--cc-arg',action='append',default=[])
a=p.parse_args();source=a.source.resolve(strict=True).read_text()
start=source.index('void* CmsAlloc(');end=source.index('#endif',start)
callbacks=source[start:end]
for name in ('cmsOpenProfileFromMemTHR','cmsCreate_sRGBProfileTHR','cmsCreateTransformTHR',
             'cmsDeleteTransform(transform_)','cmsDeleteContext(context_)'):
    assert name in source,name
with tempfile.TemporaryDirectory(prefix='pdfium-lcms-context-') as temp:
    root=Path(temp);test=root/'test.cpp';binary=root/'test'
    test.write_text('''#include <lcms2.h>
#include <lcms2_plugin.h>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <memory>
#include <type_traits>
static int allocs=0, frees=0; static bool fail_next=false;
void* FXMEM_DefaultAlloc(size_t size) { ++allocs; if(fail_next) { fail_next=false; return nullptr; } return std::malloc(size); }
void* FXMEM_DefaultRealloc(void* p, size_t size) { return std::realloc(p,size); }
void FXMEM_DefaultFree(void* p) { ++frees; std::free(p); }
'''+callbacks+'''
int main() {
 void* empty=CmsDup(nullptr,nullptr,8); if(!empty)return 1; CmsFree(nullptr,empty);
 fail_next=true; char one=0; if(CmsDup(nullptr,&one,1))return 2;
 {
  ScopedCmsContext context(cmsCreateContext(&kPdfiumMemoryPlugin,nullptr)); if(!context)return 3;
  int before=allocs; cmsHPROFILE global=cmsCreate_sRGBProfile(); if(!global)return 4; cmsCloseProfile(global);
  if(allocs!=before)return 5;
  cmsHPROFILE src=cmsCreate_sRGBProfileTHR(context.get()), dst=cmsCreate_sRGBProfileTHR(context.get());
  if(!src||!dst)return 6;
  cmsHTRANSFORM transform=cmsCreateTransformTHR(context.get(),src,TYPE_RGB_8,dst,TYPE_BGR_8,INTENT_PERCEPTUAL,0);
  cmsCloseProfile(src); cmsCloseProfile(dst); if(!transform)return 7;
  unsigned char input[3]={255,0,0}, output[3]={0}; cmsDoTransform(transform,input,output,1);
  cmsDeleteTransform(transform); if(output[0]>2||output[1]>2||output[2]<253)return 8;
 }
 return allocs>0 && frees>0 ? 0 : 9;
}\n''')
    command=[str(a.cc.resolve(strict=True)),*a.cc_arg,'-I'+str(a.include.resolve(strict=True)),str(test),
             str(a.library.resolve(strict=True)),'-Wl,-rpath,'+str(a.library.resolve().parent),'-o',str(binary)]
    subprocess.run(command,check=True,capture_output=True)
    subprocess.run([str(binary)],check=True,capture_output=True)
print('PASS: PDFium LCMS context callbacks, THR transform and global isolation')
