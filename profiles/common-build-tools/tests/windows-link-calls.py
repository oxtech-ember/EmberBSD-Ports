#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
from pathlib import Path
import re
import argparse
parser = argparse.ArgumentParser(description='Audit the actual Windows link declarations in selected registry sources')
parser.add_argument('--vendor', type=Path, action='append', required=True)
args = parser.parse_args()
roots = args.vendor
names=('chrono-0.4.45','jiff-0.2.38','libloading-0.9.0','parking_lot_core-0.9.12','windows-core-0.62.2','windows-result-0.4.1','windows-strings-0.5.1')
pattern=re.compile(r'(?:windows_link|windows_core)::link!\s*\(\s*"[^"\n]+"\s+"[^"\n]+"\s+(?:"[^"\n]+"\s+)?fn\s+([A-Za-z_]\w*)\s*\(')
count=0;problems=[]
for name in names:
 root=next((p/name for p in roots if (p/name).is_dir()),None)
 if root is None:problems.append(name+': missing source');continue
 for file in root.rglob('*.rs'):
  text=file.read_text();starts=list(re.finditer(r'(?:windows_link|windows_core)::link!\s*\(',text));matches=list(pattern.finditer(text))
  if len(starts)!=len(matches):problems.append(name+': unsupported macro prefix in '+str(file.relative_to(root)))
  decls=set(re.findall(r'\b(?:struct|enum|union|trait|type)\s+([A-Za-z_]\w*)',text));seen={}
  for m in matches:
   fn=m.group(1);count+=1;depth=1;i=m.end()
   while i<len(text) and depth:
    if text[i]=='(':depth+=1
    elif text[i]==')':depth-=1
    i+=1
   if depth:problems.append(name+': unbalanced declaration '+fn);continue
   suffix=re.match(r'\s*(?:(->)\s*([^;]+?))?\s*\)\s*;',text[i:],re.S)
   if not suffix:problems.append(name+': unsupported macro suffix '+fn)
   if fn in decls:problems.append(name+': possible type alias collision '+fn+' in '+str(file.relative_to(root)))
   imports=re.findall(r'(?m)^\s*(?:pub(?:\([^)]*\))?\s+)?use\s+[^;]+;',text,re.S)
   if any(re.search(r'\b'+re.escape(fn)+r'\b',item) for item in imports):problems.append(name+': possible imported type alias collision '+fn+' in '+str(file.relative_to(root)))
   seen[fn]=seen.get(fn,0)+1
  for fn,n in seen.items():
   if n>1:problems.append(name+': repeated macro name '+fn+' in '+str(file.relative_to(root)))
print('audited',count,'actual windows_link macro invocations across',len(names),'crate sources')
if problems:
 print('\n'.join(problems));raise SystemExit(1)
print('PASS: declarations match the new grammar; no same-file type-name collisions found')
