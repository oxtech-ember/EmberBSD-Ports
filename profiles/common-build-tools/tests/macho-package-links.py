#!/usr/bin/env python3
"""Exercise staged Mach-O symlinks against installed decoys."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('awk', 'scanner', 'readlink', 'od', 'lipo', 'otool', 'image', 'expected-library'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
with tempfile.TemporaryDirectory(prefix='macho-package-links-') as tmp:
    root = Path(tmp)
    prefix = root / 'prefix'
    stage = root / 'destdir' / prefix.relative_to('/')
    (prefix / 'bin').mkdir(parents=True)
    (stage / 'bin').mkdir(parents=True)
    shutil.copy2(a.image, prefix / 'bin/target')
    plist = root / 'plist'
    plist.write_text('bin/link\nbin/target\n')
    deps = root / 'deps'
    deps.write_text('')
    requires = root / 'requires'
    env = dict(os.environ, DESTDIR=str(root / 'destdir'), PREFIX=str(prefix),
               PACKAGE_PLIST=str(plist), MACHO_READLINK=a.readlink,
               MACHO_OD=a.od, MACHO_LIPO=a.lipo, MACHO_OTOOL=a.otool,
               MACHO_USE_LOAD_COMMANDS='yes', SKIP_SYSTEM_LIBS='1',
               DEPENDS_FILE=str(deps), PKG_INFO_CMD='/usr/bin/false',
               REQUIRES_FILE=str(requires))
    link = stage / 'bin/link'
    target = stage / 'bin/target'
    def scan():
        requires.write_text('')
        result = subprocess.run([a.awk, '-f', a.scanner], input=str(link) + '\n',
                                text=True, env=env, capture_output=True, check=True)
        return result.stdout, requires.read_text()
    link.symlink_to(prefix / 'bin/target')
    env['PACKAGE_PLIST'] = str(root / 'missing-plist')
    out, _ = scan()
    assert 'cannot read package list' in out, out
    env['PACKAGE_PLIST'] = str(plist)
    out, _ = scan()
    assert 'missing input image' in out, out
    target.write_bytes(b'not a Mach-O')
    out, found = scan()
    assert not out and not found, (out, found)
    target.unlink()
    shutil.copy2(a.image, target)
    out, found = scan()
    assert not out and a.expected_library in found, (out, found)
    link.unlink()
    link.symlink_to('target')
    out, found = scan()
    assert not out and a.expected_library in found, (out, found)
    target.unlink()
    plist.write_text('bin/link\n')
    link.unlink()
    link.symlink_to(prefix / 'bin/target')
    out, found = scan()
    assert not out and a.expected_library in found, (out, found)
    plist.write_text('bin/link\nbin/target\n')
    link.unlink()
    link.symlink_to('target')
    target.symlink_to('link')
    out, _ = scan()
    assert 'symbolic link cycle' in out, out
print('PASS: staged absolute and relative links, decoys, missing target and cycle')
