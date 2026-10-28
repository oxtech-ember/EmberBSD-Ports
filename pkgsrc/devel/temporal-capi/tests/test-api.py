#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Compile and run C/C++ users against a selected Temporal C API library."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
p = argparse.ArgumentParser()
for name in ('include', 'node-headers', 'library', 'cc', 'cxx', 'nm', 'install-name-tool'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--flag', action='append', default=[])
a = p.parse_args()
for name in ('include', 'node_headers', 'library', 'cc', 'cxx', 'nm', 'install_name_tool'):
    value = getattr(a, name).absolute()
    if not value.exists():
        raise FileNotFoundError(value)
    setattr(a, name, value)
files = Path(__file__).resolve().parent
symbols = set()
for header in a.node_headers.rglob('*.hpp'):
    symbols.update(re.findall(r'\b(temporal_rs_[A-Za-z0-9_]+)\s*\(', header.read_text()))
assert symbols, 'Node Temporal headers contain no C function declarations'
nm = subprocess.run([str(a.nm), '--defined-only', '--extern-only', str(a.library)],
                    text=True, capture_output=True, check=True)
exports = set(re.findall(r'\b_?(temporal_rs_[A-Za-z0-9_]+)\b', nm.stdout))
assert not symbols - exports, 'missing exports: ' + ', '.join(sorted(symbols - exports))
with tempfile.TemporaryDirectory(prefix='temporal-api-') as d:
    temp = Path(d); lib = temp / 'libtemporal_capi.dylib'
    shutil.copyfile(a.library, lib)
    subprocess.run([str(a.install_name_tool), '-id', str(lib), str(lib)], check=True)
    cases = [('C', a.cc, files/'consumer.c', a.include/'temporal_capi', 'c11'),
             ('C++ current', a.cxx, files/'consumer.cpp', a.include, 'c++20'),
             ('C++ Node', a.cxx, files/'consumer.cpp', a.node_headers, 'c++20')]
    for index, (label, compiler, source, include, standard) in enumerate(cases):
        exe = temp / ('consumer-' + str(index))
        subprocess.run([str(compiler), *a.flag, '-std='+standard, '-I'+str(include),
                        str(source), str(lib), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
print(f'{len(symbols)} Node C function names and C/current-C++/Node-C++ execution: PASS')
