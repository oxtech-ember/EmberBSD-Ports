#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Install project and vendored upstream license texts with source identities."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tomllib

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--vendor', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
source = a.source.resolve(strict=True)
vendor = a.vendor.resolve(strict=True)
out = a.output
out.mkdir(parents=True, exist_ok=True)
records = {}
licenses = []
def install(src, relative):
    if src.is_symlink() or not src.is_file():
        raise ValueError('license input is not a regular file: ' + str(src))
    dest = out / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    records[relative.as_posix()] = hashlib.sha256(dest.read_bytes()).hexdigest()
for src in sorted((source / 'LICENSES').rglob('*')):
    if src.is_file():
        install(src, Path('project') / src.relative_to(source))
for rel in ('REUSE.toml', 'rust/Cargo.lock'):
    install(source / rel, Path('project') / rel)
for crate in sorted(vendor.iterdir()):
    if crate.is_symlink() or not crate.is_dir():
        raise ValueError('invalid vendor directory: ' + str(crate))
    package = tomllib.loads((crate / 'Cargo.toml').read_text())['package']
    licenses.append({'name': package['name'], 'version': package['version'],
                     'license': package.get('license'), 'license_file': package.get('license-file')})
    for src in sorted(crate.rglob('*')):
        if src.is_symlink():
            raise ValueError('unexpected vendor symlink: ' + str(src))
        if not src.is_file():
            continue
        name = src.name.lower()
        if name == 'cargo.toml' or name.startswith(('license', 'licence', 'copying', 'notice')):
            install(src, Path('vendor') / crate.name / src.relative_to(crate))
(out / 'licenses.json').write_text(json.dumps(licenses, indent=2) + '\n')
(out / 'NOTICES.sha256').write_text(''.join(v + '  ' + k + '\n' for k, v in sorted(records.items())))
