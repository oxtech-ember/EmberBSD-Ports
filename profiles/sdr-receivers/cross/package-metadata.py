#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; derive package library metadata from actual staged ELF files.
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

if len(sys.argv) != 9:
    raise SystemExit('Usage: package-metadata.py STAGED_PREFIX READELF SYSROOT PLIST BUILD_INFO OUTPUT BASE_ROOT LOADER')
stage, readelf, sysroot, plist, info, output, base, loader = map(Path, sys.argv[1:])
for path in (stage, readelf, sysroot, plist, info, output, base, loader):
    if not path.is_absolute():
        raise SystemExit('Absolute paths required')
if output.exists() or output.is_symlink():
    raise SystemExit('Refusing existing output')
if not os.access(readelf, os.X_OK):
    raise SystemExit('Select an executable target readelf')
expected = sorted(line for line in plist.read_text().splitlines() if line and not line.startswith('@'))
actual = sorted(str(path.relative_to(stage)) for path in stage.rglob('*') if path.is_file() or path.is_symlink())
if expected != actual:
    raise SystemExit('Expanded PLIST does not match staged payload')
metadata = info.read_text().splitlines()
architectures = [line.split('=', 1)[1] for line in metadata if line.startswith('MACHINE_ARCH=')]
if len(architectures) != 1 or architectures[0] not in ('x86_64', 'aarch64'):
    raise SystemExit('One supported target MACHINE_ARCH is required')
machine = {'x86_64': 62, 'aarch64': 183}[architectures[0]]

def inspect(path):
    data = path.read_bytes()
    if data[:4] != b'\x7fELF':
        return None
    if data[4:6] != b'\x02\x01' or int.from_bytes(data[18:20], 'little') != machine:
        raise SystemExit('Unexpected target ELF: ' + str(path))
    text = subprocess.check_output([str(readelf), '-l', '-d', str(path)], text=True)
    for line in text.splitlines():
        if any(tag in line for tag in ('RPATH', 'RUNPATH', 'NEEDED')) and any(str(root) in line for root in (stage, sysroot)):
            raise SystemExit('Host path in ELF dependency: ' + str(path))
    return {'needed': re.findall(r'\(NEEDED\).*?\[([^]]+)\]', text),
            'soname': re.findall(r'\(SONAME\).*?\[([^]]+)\]', text),
            'interpreter': re.findall(r'Requesting program interpreter: ([^\]]+)', text)}

def copy_base(source, destination):
    if not source.resolve().is_relative_to(sysroot.resolve()):
        raise SystemExit('Base input escapes sysroot')
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).digest()
    if destination.exists():
        if destination.is_symlink() or hashlib.sha256(destination.read_bytes()).digest() != digest:
            raise SystemExit('Conflicting base closure input')
    else:
        shutil.copyfile(source, destination)
        destination.chmod(source.stat().st_mode & 0o777)

provided = set()
needed = set()
for path in sorted(stage.rglob('*')):
    if path.is_symlink() and not path.resolve().is_relative_to(stage.resolve()):
        raise SystemExit('Package link escapes staged prefix')
    if not path.is_file():
        continue
    elf = inspect(path)
    if not elf:
        continue
    if elf['soname']:
        provided.add('/usr/pkg/' + str(path.relative_to(stage)))
    needed.update(elf['needed'])
    for interpreter in elf['interpreter']:
        if not interpreter.startswith('/') or '..' in Path(interpreter).parts:
            raise SystemExit('Unsafe ELF interpreter path')
        copy_base(loader, base / interpreter.lstrip('/'))

requires = set()
queue = list(needed)
seen = set()
while queue:
    name = queue.pop()
    if name in seen:
        continue
    seen.add(name)
    if '/' in name or name in ('.', '..'):
        raise SystemExit('Expected a dependency SONAME')
    candidates = ['/usr/pkg/gcc16/lib/' + name, '/usr/pkg/lib/' + name, '/usr/lib/' + name, '/lib/' + name]
    own = [path for path in candidates if path in provided]
    if own:
        continue
    found = next((path for path in candidates if (sysroot / path.lstrip('/')).is_file()), None)
    if not found:
        raise SystemExit('Unresolved target dependency: ' + name)
    requires.add(found)
    if found.startswith(('/usr/lib/', '/lib/')):
        source = sysroot / found.lstrip('/')
        copy_base(source, base / found.lstrip('/'))
        elf = inspect(source)
        if elf:
            queue.extend(elf['needed'])
metadata = [line for line in metadata if not line.startswith(('PROVIDES=', 'REQUIRES='))]
output.write_text('\n'.join(metadata + ['PROVIDES=' + path for path in sorted(provided)] +
                            ['REQUIRES=' + path for path in sorted(requires)]) + '\n')
print(f'PASS ELF metadata: {len(provided)} provides, {len(requires)} external requirements')
