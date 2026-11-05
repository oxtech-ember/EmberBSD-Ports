#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run installed WebP and JPEG 12/16-bit functionality on the native host."""
import argparse, subprocess, tempfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('cc','prefix','sysroot'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(); prefix=a.prefix.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='electron-image-runtime-') as td:
 root=Path(td); binary=root/'webp-smoke'
 source=Path(__file__).with_name('image-codec-smoke.c')
 command=[str(a.cc),'-isysroot',str(a.sysroot),'-I'+str(prefix/'include'),'-I'+str(prefix/'include/webp'),
          str(source),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),
          '-lwebp','-lwebpdemux','-lwebpmux','-lsharpyuv','-o',str(binary)]
 subprocess.run(command,check=True);subprocess.run([str(binary)],check=True)
 data=b'P5\n2 2\n65535\n'+bytes.fromhex('00008000c000ffff'); src=root/'input.pgm';src.write_bytes(data)
 for bits in (12,16):
  jpeg=root/f'{bits}.jpg'; out=root/f'{bits}.pgm'; command=[str(prefix/'bin/cjpeg'),'-precision',str(bits)]
  if bits==16:command+=['-lossless','1']
  subprocess.run(command+['-outfile',str(jpeg),str(src)],check=True)
  cmd=[str(prefix/'bin/djpeg')]+(['-precision','12'] if bits==12 else [])
  subprocess.run(cmd+['-outfile',str(out),str(jpeg)],check=True)
  content=out.read_bytes(); assert content.startswith(b'P5\n2 2\n'+(b'4095\n' if bits==12 else b'65535\n'))
  if bits==16: assert content==data
print('PASS: installed WebP and JPEG 12/16-bit encode/decode')
