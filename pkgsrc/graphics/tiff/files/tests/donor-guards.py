#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Test selected TIFF source guards and the actual built libtiff strip reader."""
import argparse, pathlib, re, struct, subprocess, tempfile
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','baseline-source','build','cc'):p.add_argument('--'+name,type=pathlib.Path,required=True)
p.add_argument('--cc-arg',action='append',default=[])
a=p.parse_args(); source=a.source.resolve(strict=True); build=a.build.resolve(strict=True)
cc=[str(a.cc.resolve(strict=True)),*a.cc_arg]; tests=pathlib.Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='tiff-guards-') as tmp:
 root=pathlib.Path(tmp)
 # Exercise the built implementation with a normal image and 2^31 strips;
 # the limit prevents a large allocation even against an unpatched library.
 for name,height in [('ordinary',1),('excess',2**31)]:
  tags=[(256,4,1,1),(257,4,1,height),(258,3,1,8),(259,3,1,1),(262,3,1,1),(273,4,1,256),(277,3,1,1),(278,4,1,1),(279,4,1,1)]
  data=b'II'+struct.pack('<HIH',42,8,len(tags))+b''.join(struct.pack('<HHII',*x) for x in tags)+struct.pack('<I',0)
  (root/(name+'.tif')).write_bytes(data.ljust(257,b'\x00'))
 binary=root/'strip-check'; lib=build/'libtiff'
 subprocess.run(cc+['-I'+str(lib),'-I'+str(source/'libtiff'),str(tests/'strip-count.c'),'-L'+str(lib),'-Wl,-rpath,'+str(lib),'-ltiff','-o',str(binary)],check=True)
 for name in ('ordinary','excess'):
  subprocess.run([str(binary),str(root/(name+'.tif')),'normal' if name=='ordinary' else 'excess'],check=True)
 # Compile and evaluate the actual changed comparison and row expression with
 # boundary values, including a >4 GiB destination on 64-bit and UBSan.
 pix=(source/'libtiff/tif_pixarlog.c').read_text()
 match=re.search(r'Check that we will not fill more than what was allocated \*/\s*if \((.*?)\)\s*\{',pix,re.S)
 if not match: raise ValueError('missing guarded PixarLog comparison')
 baseline=(a.baseline_source.resolve(strict=True)/'libtiff/tif_pixarlog.c').read_text()
 oldmatch=re.search(r'Check that we will not fill more than what was allocated \*/\s*if \((.*?)\)\s*\{',baseline,re.S)
 if not oldmatch: raise ValueError('missing baseline PixarLog comparison')
 f=root/'pixar-boundary.c';exe=root/'pixar-boundary'
 test='''#include <stdint.h>\ntypedef WIDTH tmsize_t;\nstruct S { tmsize_t tbuf_size; struct { uint32_t avail_out; } stream; };\nint main(void) { struct S value={2147483647,{2147483648u}}, *sp=&value; if (!(EXPR)) return 1; value.tbuf_size=100; value.stream.avail_out=99; if (EXPR) return 2; if (sizeof(tmsize_t)>4) { value.tbuf_size=(tmsize_t)((int64_t)1<<32); if (EXPR) return 3; } return 0; }\n'''
 for width in ('int32_t','int64_t'):
  for label,expression in (('baseline',oldmatch.group(1)),('patched',match.group(1))):
   f.write_text(test.replace('WIDTH',width).replace('EXPR',expression))
   subprocess.run(cc+['-fsanitize=undefined','-fno-sanitize-recover=undefined',str(f),'-o',str(exe)],check=True)
   result=subprocess.run([str(exe)])
   expected=1 if (width,label)==('int32_t','baseline') else 0
   if result.returncode != expected: raise AssertionError((width,label,result.returncode,expected))
 text=(source/'libtiff/tif_getimage.c').read_text()
 matchrow=re.search(r'rowstoread = rowsperstrip -\s*(.*?) % rowsperstrip;',text[text.index('static int gtStripContig('):],re.S)
 if not matchrow: raise ValueError('missing contiguous-strip row calculation')
 expr=matchrow.group(1)
 guard=re.search(r'TIFFRGBAImageGet has already validated the nonnegative row offset\. \*/\s*if \((.*?)\)\s*return 0;',text[text.index('static int gtStripContig('):],re.S)
 if not guard: raise ValueError('missing TIFF-sized strip bounds')
 c='''#include <stdint.h>\n#include <stddef.h>\nstruct S { int64_t tbuf_size; struct { uint32_t avail_out; } stream; };\nstruct I { int32_t row_offset; };\nint main(void) {\n struct S state={-1,{3}}, *sp=&state;\n if (!(EXPR)) return 1;\n state.tbuf_size=((int64_t)1<<32); if (EXPR) return 2;\n state.tbuf_size=2; if (!(EXPR)) return 3;\n struct I value={1}, *img=&value; uint32_t row=2147483647u, rowsperstrip=16;\n uint32_t rowstoread=rowsperstrip - ROW % rowsperstrip;\n return rowstoread!=16;\n}\n'''.replace('EXPR',match.group(1)).replace('ROW',expr)
 f=root/'boundary.c'; f.write_text(c);exe=root/'boundary'
 subprocess.run(cc+['-fsanitize=undefined','-fno-sanitize-recover=undefined',str(f),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
 check='''#include <stdint.h>\nstruct I { int32_t row_offset; };\nint test(uint32_t h) { struct I i={0}, *img=&i; if (COND) return 1; return 0; }\nint main(void) { return test(2147483648u)!=EXPECTED; }\n'''.replace('COND',guard.group(1))
 for maximum,expected in (('2147483647LL','1'),('9223372036854775807LL','0')):
  f.write_text('#define TIFF_TMSIZE_T_MAX '+maximum+'\n'+check.replace('EXPECTED',expected))
  subprocess.run(cc+['-fsanitize=undefined','-fno-sanitize-recover=undefined',str(f),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
print('PASS: strip count, PixarLog bounds and signed-row boundary')
