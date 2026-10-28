#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Install metadata and original license notices for locked Rust inputs."""
import argparse, hashlib, json, re, shutil, tomllib
from pathlib import Path
p = argparse.ArgumentParser()
for n in ('lock', 'vendor', 'output'): p.add_argument('--'+n, type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
rows = []
for item in tomllib.loads(a.lock.read_text())['package']:
    if 'source' not in item: continue
    assert item['source'] == 'registry+https://github.com/rust-lang/crates.io-index'
    name = item['name'] + '-' + item['version']
    assert re.fullmatch(r'[A-Za-z0-9_.+-]+', name), name
    source = a.vendor / name
    meta = tomllib.loads((source/'Cargo.toml').read_text())['package']
    checksum = json.loads((source/'.cargo-checksum.json').read_text())['package']
    assert (meta['name'], meta['version'], checksum) == (item['name'], item['version'], item['checksum'])
    notices = [x for x in source.rglob('*') if x.is_file() and not x.is_symlink() and x.name.upper().startswith(('LICENSE', 'LICENCE', 'COPYING', 'NOTICE', 'AUTHORS'))]
    output = a.output/name
    output.mkdir()
    shutil.copyfile(source/'Cargo.toml', output/'Cargo.toml')
    for path in notices:
        dest = output / path.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    rows.append({'name': name, 'checksum': checksum, 'license': meta.get('license'),
                 'notices': [str(x.relative_to(source)) for x in notices]})
(a.output/'index.json').write_text(json.dumps(rows, indent=2)+'\n')
print('preserved license metadata and notices for', len(rows), 'locked crates')
