#!/usr/bin/env python3
"""Link the regular patched vendor into a separately extracted test vendor."""
import argparse
from pathlib import Path
import shutil
p = argparse.ArgumentParser()
p.add_argument('--work', type=Path, required=True)
p.add_argument('--test-work', type=Path, required=True)
p.add_argument('--fixtures', type=Path, required=True)
a = p.parse_args()
normal = a.work / 'vendor'
output = a.test_work
vendor = output / 'vendor'
if not normal.is_dir() or not (a.work / '.cargo/ember-config.toml').is_file():
    raise SystemExit('Build the normal provider first')
for item in normal.iterdir():
    if item.is_dir():
        link = vendor / item.name
        if not link.exists() and not link.is_symlink():
            link.symlink_to(item.resolve(), target_is_directory=True)
(output / 'src').mkdir(parents=True, exist_ok=True)
for name in ('Cargo.toml', 'Cargo.lock'):
    shutil.copy2(a.fixtures / ('crypto-' + name), output / name)
shutil.copy2(a.fixtures / 'crypto-inout-features.rs', output / 'src/main.rs')
config = (a.work / '.cargo/ember-config.toml').read_text()
for before, after in ((normal, vendor), (a.work / 'cargo-target', output / 'target')):
    if str(before) not in config:
        raise SystemExit('Normal cargo configuration does not match work directory')
    config = config.replace(str(before), str(after))
(output / '.cargo/config.toml').write_text(config)
