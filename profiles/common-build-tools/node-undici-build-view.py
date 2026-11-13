#!/usr/bin/env python3
"""Prepare the selected Undici loader beside a native Node snapshot tool."""
import argparse
import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--pkg-info', required=True, type=Path)
p.add_argument('--pkgdb', required=True, type=Path)
p.add_argument('--prefix', required=True, type=Path)
p.add_argument('--runtime-prefix', required=True, type=Path)
p.add_argument('--out', required=True, type=Path)
p.add_argument('--recipe', required=True, type=Path)
p.add_argument('--python', required=True, type=Path)
a = p.parse_args()
for path in (a.pkg_info, a.pkgdb, a.prefix, a.runtime_prefix, a.out, a.recipe, a.python):
    if not path.is_absolute():
        raise SystemExit('all paths must be absolute')
result = subprocess.run([str(a.pkg_info), '-K', str(a.pkgdb), '-E', 'undici>=8.12.4'], check=True, capture_output=True, text=True).stdout.splitlines()
if len(result) != 1 or not re.fullmatch(r'undici-[A-Za-z0-9._+-]+', result[0]):
    raise SystemExit('selected Undici package missing or ambiguous')
package = a.pkgdb / result[0]
info = (package / '+BUILD_INFO').read_text().splitlines()
if 'PKGPATH=www/undici' not in info or f'EMBERBSD_UNDICI_RUNTIME_PREFIX={a.runtime_prefix}' not in info:
    raise SystemExit('selected Undici owner or runtime prefix differs')
metadata = {}
for line in (package / '+BUILD_VERSION').read_text().splitlines():
    name, separator, digest = line.partition(': ')
    if not separator or name in metadata:
        raise SystemExit('invalid Undici source metadata')
    metadata[name] = digest
for name in ('Makefile', 'distinfo', 'files/generate-wasm.py'):
    path = a.recipe / name
    if not path.is_file() or metadata.get('www/undici/' + name) != hashlib.sha256(path.read_bytes()).hexdigest():
        raise SystemExit('selected Undici source differs: ' + name)
relative = Path('lib/node_modules/undici/loader.js')
contents = (package / '+CONTENTS').read_text().splitlines()
indices = [i for i, line in enumerate(contents) if line == str(relative)]
if len(indices) != 1 or indices[0] + 1 >= len(contents):
    raise SystemExit('selected Undici does not uniquely own its loader')
match = re.fullmatch(r'@comment MD5:([0-9a-f]{32})', contents[indices[0] + 1])
loader = a.prefix / relative
if not match or loader.is_symlink() or not loader.is_file() or not loader.resolve().is_relative_to(a.prefix.resolve()):
    raise SystemExit('invalid selected Undici loader')
data = loader.read_bytes()
if hashlib.md5(data, usedforsecurity=False).hexdigest() != match.group(1):
    raise SystemExit('selected Undici loader checksum differs')
logical = a.runtime_prefix / relative
if ('createRequire("' + str(logical) + '")').encode() not in data:
    raise SystemExit('selected Undici loader runtime path differs')
wasi = subprocess.run([str(a.pkg_info), '-K', str(a.pkgdb), '-E', 'llhttp-wasi>=9.4.4'], check=True, capture_output=True, text=True).stdout.splitlines()
if len(wasi) != 1 or not re.fullmatch(r'llhttp-wasi-[A-Za-z0-9._+-]+', wasi[0]):
    raise SystemExit('selected llhttp-wasi package missing or ambiguous')
wasi_package = a.pkgdb / wasi[0]
if 'PKGPATH=www/llhttp-wasi' not in (wasi_package / '+BUILD_INFO').read_text().splitlines():
    raise SystemExit('selected llhttp-wasi owner differs')
wasi_contents = (wasi_package / '+CONTENTS').read_text().splitlines()
for name in ('llhttp.wasm', 'llhttp_simd.wasm'):
    relative_wasm = 'share/llhttp-wasi/' + name
    matches = [i for i, line in enumerate(wasi_contents) if line == relative_wasm]
    if len(matches) != 1 or matches[0] + 1 >= len(wasi_contents):
        raise SystemExit('selected llhttp-wasi does not uniquely own ' + name)
    checksum = re.fullmatch(r'@comment MD5:([0-9a-f]{32})', wasi_contents[matches[0] + 1])
    wasm = a.prefix / relative_wasm
    if (not checksum or wasm.is_symlink() or not wasm.is_file() or
            not wasm.resolve().is_relative_to(a.prefix.resolve()) or
            hashlib.md5(wasm.read_bytes(), usedforsecurity=False).hexdigest() != checksum.group(1)):
        raise SystemExit('selected llhttp-wasi content differs: ' + name)
with tempfile.TemporaryDirectory(prefix='node-undici-generator-') as temporary:
    temporary = Path(temporary)
    generated = temporary / 'loader.js'
    subprocess.run([str(a.python), '-B', '-I', '-S', str(a.recipe / 'files/generate-wasm.py'),
                    '--wasm-dir', str(a.prefix / 'share/llhttp-wasi'),
                    '--output-dir', str(temporary), '--loader', str(generated),
                    '--install-dir', str(a.prefix / 'lib/node_modules/undici')], check=True)
    data = generated.read_bytes()
if ('createRequire("' + str(a.prefix / relative) + '")').encode() not in data:
    raise SystemExit('generated build loader has incorrect provider path')
if a.out.is_symlink() or not a.out.is_dir() or a.out.resolve() != a.out:
    raise SystemExit('build output must be an existing canonical real directory')
parent = a.out
for part in ('lib', 'node_modules', 'undici'):
    parent = parent / part
    try:
        parent.mkdir()
    except FileExistsError:
        pass
    if parent.is_symlink() or not parent.is_dir():
        raise SystemExit('build provider directory is not a real directory')
target = parent / 'loader.js'
if os.path.lexists(target):
    if target.is_symlink() or not target.is_file() or target.read_bytes() != data:
        raise SystemExit('existing build provider differs')
else:
    with target.open('xb') as stream:
        stream.write(data)
print(f'prepared selected {result[0]} loader')
