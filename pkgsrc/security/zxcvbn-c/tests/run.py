#!/usr/bin/env python3
"""Run explicit host regressions with a caller-selected native compiler."""
import argparse
from pathlib import Path
import subprocess
p=argparse.ArgumentParser()
p.add_argument('--cc',required=True,type=Path)
p.add_argument('--engine',required=True,type=Path,help='directory containing engine and dictionary API sources')
p.add_argument('--dictionary',required=True,type=Path,help='directory containing generated dict-src.h')
p.add_argument('--output',required=True,type=Path)
p.add_argument('--sanitize',action='store_true')
a=p.parse_args()
if not a.cc.is_absolute() or not a.cc.is_file(): raise SystemExit('Select an absolute SDK native compiler')
a.output.mkdir(parents=True,exist_ok=True)
here=Path(__file__).resolve().parent
for name in ['adversarial','actual-dictionary']:
 command=[str(a.cc),'-std=c11','-O1','-g','-Wall','-Wextra','-I'+str(a.engine),'-I'+str(a.dictionary),str(here/(name+'.c')),str(a.engine/'zxcvbn.c'),str(a.engine/'zxcvbn-dictionary.c'),'-lm','-pthread','-o',str(a.output/name)]
 if a.sanitize: command[1:1]=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
 subprocess.run(command,check=True)
 subprocess.run([str(a.output/name)],check=True)
