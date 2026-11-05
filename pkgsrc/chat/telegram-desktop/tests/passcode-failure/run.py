#!/usr/bin/env python3
"""Test actual Telegram strength code with an injected dictionary failure."""
import argparse
from pathlib import Path
import shlex, subprocess
p=argparse.ArgumentParser()
p.add_argument('--cxx',type=Path,required=True)
p.add_argument('--pkg-config',type=Path,required=True)
p.add_argument('--prefix',type=Path,required=True)
p.add_argument('--source',type=Path,required=True,help='Telegram/SourceFiles')
p.add_argument('--engine-headers',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
for tool in (a.cxx,a.pkg_config):
 if not tool.is_absolute() or not tool.is_file(): raise SystemExit('Select absolute SDK tools')
a.output.mkdir(parents=True,exist_ok=True)
flags=shlex.split(subprocess.check_output([str(a.pkg_config),'--cflags','--libs','Qt6Core'],text=True))
cmd=[str(a.cxx),'-std=c++20','-O2','-DTDESKTOP_USE_PACKAGED_ZXCVBN','-I'+str(a.source),'-I'+str(a.engine_headers),'-I'+str(a.prefix/'include'),str(Path(__file__).with_name('test.cpp')),str(a.source/'ui/passcode_strength.cpp'),str(a.source/'ui/passcode_strength_translit.cpp'),*flags,'-o',str(a.output/'passcode-failure')]
subprocess.run(cmd,check=True); subprocess.run([str(a.output/'passcode-failure')],check=True)
