#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check pkg_admin alternate-root resolution and package metadata."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pkg-admin', required=True, type=Path)
parser.add_argument('--work-dir', required=True, type=Path)
args = parser.parse_args()
if not args.pkg_admin.is_absolute() or not args.work_dir.is_absolute():
    parser.error('absolute paths required')

with tempfile.TemporaryDirectory(prefix='pkgadmin-rooted-', dir=args.work_dir) as tmp:
    root = Path(tmp)
    stage = root / 'stage'
    db = stage / 'db'
    pkg = db / 'fixture-1.0'
    pkg.mkdir(parents=True)
    (stage / 'target').mkdir()
    (stage / 'target/regular').write_text('data')
    (stage / 'a').mkdir()
    (stage / 'a/relative').symlink_to('../target/regular')
    (stage / 'a/absolute').symlink_to('/target/regular')
    (stage / 'a/chain').symlink_to('absolute')
    (stage / 'dirlink').symlink_to('/target')
    (stage / 'a/dir').symlink_to('/target')
    (stage / 'loop1').symlink_to('/loop2')
    (stage / 'loop2').symlink_to('/loop1')
    content = pkg / '+CONTENTS'

    def check(plist, success=True):
        content.write_text('@name fixture-1.0\n' + plist)
        result = subprocess.run([str(args.pkg_admin), '-P', str(stage), '-K', str(db),
                                 'check', 'fixture-1.0'], capture_output=True, text=True)
        if (result.returncode == 0) != success:
            raise AssertionError((result.returncode, result.stdout, result.stderr))

    for name, target in [('relative', '../target/regular'), ('absolute', '/target/regular'),
                         ('chain', 'absolute'), ('dir', '/target')]:
        check('@cwd /a\n' + name + '\n@comment Symlink:' + target + '\n')
    check('@cwd /a\nrelative\n@comment Symlink:wrong-target\n', False)
    checksum = hashlib.md5(b'data').hexdigest()
    check('@cwd /dirlink\nregular\n@comment MD5:' + checksum + '\n')
    (stage / 'target/regular').write_text('changed')
    check('@cwd /dirlink\nregular\n@comment MD5:' + checksum + '\n', False)
    (stage / 'target/regular').write_text('data')
    (pkg / 'dbfile').write_text('db')
    check('@cwd .\ndbfile\n')
    host_dir = root / 'host-dir'
    host_dir.mkdir()
    host_link = root / 'host-dir-link'
    host_link.symlink_to(host_dir)
    content.write_text('@name fixture-1.0\n@cwd ' + str(root) +
                       '\nhost-dir-link\n@comment Symlink:' + str(host_dir) + '\n')
    result = subprocess.run([str(args.pkg_admin), '-K', str(db), 'check', 'fixture-1.0'],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError((result.stdout, result.stderr))
    check('@cwd /target/regular/..\nregular\n', False)
    check('@cwd /\nloop1\n@comment Symlink:/loop2\n', False)
    # An absolute target existing only on the host cannot satisfy a stage check.
    hostonly = root / 'host-only'
    hostonly.write_text('outside')
    (stage / 'a/hostonly').symlink_to(hostonly)
    check('@cwd /a\nhostonly\n@comment Symlink:' + str(hostonly) + '\n', False)
    (stage / 'a/bad').symlink_to('/missing')
    check('@cwd /a\nbad\n@comment Symlink:/missing\n', False)
print('rooted relative/absolute/chain/directory/loop/MD5 and cwd-dot PASS')
