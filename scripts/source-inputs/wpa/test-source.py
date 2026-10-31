#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the two-archive WPA source owner and its prepared-tree checks."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser()
for name in ('sdk-source', 'git', 'archive', 'hostapd-archive', 'patch',
             'work-dir', 'pkgsrc-export'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
owner = Path(__file__).with_name('source.py')
base = [sys.executable, '-B', str(owner), '--sdk-source', str(args.sdk_source),
        '--git', str(args.git)]
with tempfile.TemporaryDirectory(dir=args.work_dir) as directory:
    tmp = Path(directory)
    root = tmp / 'prepared'

    def run(*words, success=True):
        result = subprocess.run([*base, *map(str, words), '--pkgsrc-export',
                                 str(args.pkgsrc_export)], capture_output=True, text=True)
        if (result.returncode == 0) != success:
            raise AssertionError(result.stderr)
        return result

    def prepare(archive, hostapd, output, success=True):
        return run('prepare', '--archive', archive, '--hostapd-archive', hostapd,
                   '--patch', args.patch, '--output', output, '--scoped-identity',
                   success=success)

    prepare(args.archive, args.hostapd_archive, root)
    run('verify-source', '--source', root, '--patch', args.patch)
    assert (root / 'src/drivers/driver_bsd.c').is_file()
    assert (root / 'wpa_supplicant/wpa_supplicant.c').is_file()
    assert (root / 'hostapd/main.c').is_file()
    prepare(args.archive, args.hostapd_archive, root, success=False)
    for archive, first in ((args.archive, True), (args.hostapd_archive, False)):
        bad = tmp / archive.name
        shutil.copyfile(archive, bad)
        with bad.open('r+b') as stream:
            first_byte = stream.read(1)[0]
            stream.seek(0)
            stream.write(bytes([first_byte ^ 1]))
        prepare(bad if first else args.archive, args.hostapd_archive if first else bad,
                tmp / ('bad-wpa' if first else 'bad-hostapd'), success=False)
    (root / 'unexpected').write_text('changed\n')
    assert 'payload changed' in run('verify-source', '--source', root,
                                    '--patch', args.patch, success=False).stderr
print('WPA common prepared source: PASS')
