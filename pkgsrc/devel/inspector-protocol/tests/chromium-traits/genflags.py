#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
from pathlib import Path
import argparse,re,subprocess
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--toolchain-ninja',type=Path,required=True);p.add_argument('--python',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
source=a.toolchain_ninja.read_text()
for block in source.split('\nrule '):
 if 'write_buildflag_header.py --output ' not in block: continue
 c=re.search(r'rspfile_content = (.+)',block); d=re.search(r'--output (\S+).*?--rulename (\S+)',block); script=re.search(r'\.\./src/(\S*write_buildflag_header.py)',block)
 if not c or not d or not script: continue
 output=d.group(1); f=a.output/output;f.parent.mkdir(parents=True,exist_ok=True);rsp=a.output/'flags.rsp';rsp.write_text(c.group(1)+'\n')
 subprocess.run([str(a.python),str(a.source/script.group(1)),'--output',output,'--rulename',d.group(2).replace('$:',':'),'--gen-dir',str(a.output),'--definitions',str(rsp)],check=True)
