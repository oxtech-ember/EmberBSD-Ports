#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check a prepared pkgsrc target C++ wrapper does not embed its runtime stage."""
import argparse
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ('wrapper', 'wrapper-config', 'runtime-stage', 'readelf', 'work'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
for name in ('wrapper', 'wrapper_config', 'runtime_stage', 'readelf'):
    if not getattr(args, name).is_absolute(): parser.error('--' + name.replace('_', '-') + ' must be absolute')
if not args.work.is_absolute() or args.work.exists(): parser.error('--work must be new and absolute')
args.work.mkdir(parents=True)
source = args.work / 'consumer.cc'
source.write_text('#include <string>\nint main() { return std::string("ok").size() != 2; }\n')
binary = args.work / 'consumer'
physical = str(args.runtime_stage / 'usr/pkg/llvm/lib')
env = dict(os.environ, CWRAPPERS_CONFIG_DIR=str(args.wrapper_config))
subprocess.run([str(args.wrapper), str(source), '-Wl,-rpath,' + physical, '-o', str(binary)], env=env, check=True)
text = subprocess.check_output([str(args.readelf), '-d', str(binary)], text=True)
rpaths = [line for line in text.splitlines() if 'RPATH' in line or 'RUNPATH' in line]
assert rpaths and all(str(args.runtime_stage) not in line for line in rpaths), rpaths
assert any('/usr/pkg/llvm/lib' in line for line in rpaths), rpaths
print('target cwrapper runtime-stage RPATH PASS')
