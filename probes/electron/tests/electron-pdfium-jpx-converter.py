#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compile actual PDFium SYCC converter blocks with a nullable allocator."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(); p.add_argument('--source', required=True, type=Path); p.add_argument('--cc', required=True, type=Path); p.add_argument('--include', required=True, type=Path); p.add_argument('--cc-arg', action='append', default=[]); a=p.parse_args()
s=a.source.read_text(); first=s[s.index('struct OpjImageDataDeleter'):s.index('void fx_ignore_callback')]; second=s[s.index('std::optional<OpjImageRgbData> alloc_rgb'):s.index('\n}  // namespace')]
preamble=r'''#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <type_traits>
#include <unordered_set>
#include "openjpeg.h"
static std::unordered_set<void*> owned;
static int calls, fail_at;
void* test_alloc(size_t size) { if (++calls == fail_at) return nullptr; void* p=std::malloc(size); if (p) owned.insert(p); return p; }
void test_free(void* p) { if (p) { owned.erase(p); std::free(p); } }
#define opj_image_data_alloc test_alloc
#define opj_image_data_free test_free
#define UNSAFE_BUFFERS(...) __VA_ARGS__
#define UNSAFE_TODO(...) __VA_ARGS__
namespace pdfium { using std::span; }
namespace fxcrt { template<typename A, typename B> A CeilDiv(A a,B b) { return a / b + (a % b != 0); } }
template<typename T> class Safe {
  T value_; bool valid_=true;
 public: Safe(T value): value_(value) {} Safe& operator*=(size_t n) { T out; if (__builtin_mul_overflow(value_,n,&out)) valid_=false; else value_=out; return *this; }
 Safe& operator/=(size_t n) { value_/=n; return *this; } bool IsValid() const { return valid_; } T ValueOrDie() const { if (!valid_) std::abort(); return value_; }
};
using FX_SAFE_SIZE_T=Safe<size_t>; using FX_SAFE_UINT32=Safe<uint32_t>;
'''
main=r'''
template<typename F> bool invoke(F f, opj_image_t* image) {
 if constexpr (std::is_void_v<std::invoke_result_t<F, opj_image_t*>>) { f(image); return true; }
 else return f(image);
}
int main() {
 for (int mode=0; mode<3; ++mode) for (int fail=0; fail<=3; ++fail) {
   opj_image_t image{}; opj_image_comp_t comp[3]{}; image.numcomps=3; image.comps=comp; image.color_space=OPJ_CLRSPC_SYCC;
   for (int c=0;c<3;++c) { comp[c].w=2; comp[c].h=2; comp[c].dx=1; comp[c].dy=1; comp[c].prec=8; }
   if (mode) for (int c=1;c<3;++c) { comp[c].w=1; comp[c].dx=2; if (mode==2) { comp[c].h=1; comp[c].dy=2; } }
   int* before[3];
   for (int c=0;c<3;++c) { size_t n=comp[c].w*comp[c].h; before[c]=(int*)std::malloc(n*sizeof(int)); if (!before[c]) return 10; std::fill_n(before[c],n,128); comp[c].data=before[c]; }
   calls=0;fail_at=fail; bool ok=invoke(color_sycc_to_rgb,&image);
   if (fail) {
     if (ok || image.color_space!=OPJ_CLRSPC_SYCC || !owned.empty()) return 20+mode;
     for (int c=0;c<3;++c) if (comp[c].data!=before[c]) return 30+mode;
   } else {
     if (!ok || image.color_space!=OPJ_CLRSPC_SRGB || owned.size()!=3) return 40+mode;
     for (int c=0;c<3;++c) { if (comp[c].w!=2 || comp[c].h!=2 || comp[c].dx!=1 || comp[c].dy!=1) return 50+mode; for(int i=0;i<4;++i) if(comp[c].data[i]!=128) return 60+mode; }
   }
   for (int c=0;c<3;++c) test_free(comp[c].data);
   if (!owned.empty()) return 70+mode;
 }
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='pdfium-jpx-test-') as d:
 src=Path(d)/'test.cpp';binary=Path(d)/'test';src.write_text(preamble+first+second+main)
 subprocess.run([str(a.cc),*a.cc_arg,'-std=c++20','-O1','-I'+str(a.include),str(src),'-o',str(binary)],check=True)
 subprocess.run([str(binary)],check=True)
print('PDFium actual SYCC converter nullable-allocation fixture PASS')
