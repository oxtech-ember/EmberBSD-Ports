#!/usr/bin/env python3
import argparse
from pathlib import Path
import subprocess
import tempfile
p=argparse.ArgumentParser();p.add_argument('--cc',required=True);p.add_argument('--source',required=True,type=Path);a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='pffft-arch-guards-') as d:
 root=Path(d)
 for kind in ('float','double'):
  (root/f'pf_neon_{kind}.h').write_bytes((a.source/f'src/simd/pf_neon_{kind}.h').read_bytes())
 (root/'arm_neon.h').write_text('')
 (root/'pf_neon_double_from_avx.h').write_text('')
 def enabled(kind,defines):
  cmd=[a.cc,'-E','-dM','-undef','-nostdinc','-I',str(root),'-x','c',*[f'-D{x}' for x in defines],'-']
  result=subprocess.run(cmd,input=f'#include "pf_neon_{kind}.h"\n',capture_output=True,text=True,check=True)
  return '#define SIMD_SZ 4' in result.stdout
 for kind in ('float','double'):
  assert enabled(kind,['__aarch64__','__ARM_NEON'])
  assert not enabled(kind,['__aarch64__','__ARM_NEON','PFFFT_SIMD_DISABLE'])
  assert not enabled(kind,['_M_ARM64'])
  assert not enabled(kind,['__arm__','__ARMEL__'])
 assert enabled('float',['__arm__','PFFFT_ENABLE_NEON'])
print('PFFFT ARM NEON selection guards PASS')
