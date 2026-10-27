#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted) regression for the canonical GNU patch recipe.
"""Check GNU patch 2.8 source fixes and the selected consumer command."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


SHA256 = 'f87cee69eec2b4fcbf60a396b030ad6aa3415f192aa5f7ee84cad5e11f7f5ae3'
ARCHIVE = 'patch-2.8.tar.xz'


def require(value, message):
    if not value:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--patch-tool', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    require(args.archive.is_absolute() and args.archive.is_file(),
            'Use the verified absolute GNU patch archive')
    require(args.patch_tool.is_absolute() and args.patch_tool.is_file() and
            os.access(args.patch_tool, os.X_OK),
            'Use the installed executable GNU patch provider')
    require(args.work.is_absolute() and args.work.is_dir(),
            'Use an existing scratch directory inside the workspace')
    data = args.archive.read_bytes()
    require(args.archive.name == ARCHIVE and hashlib.sha256(data).hexdigest() == SHA256,
            'Archive does not match GNU patch 2.8 official SHA256')
    with tarfile.open(args.archive, 'r:xz') as archive:
        root = 'patch-2.8/'
        def read(name):
            member = archive.getmember(root + name)
            require(member.isfile(), 'Expected regular upstream source member: ' + name)
            return archive.extractfile(member).read().decode('utf-8', errors='strict')
        news = read('NEWS')
        source = read('src/pch.c')
        test_list = read('tests/Makefile.in')
        ed_test = read('tests/ed-style')
    require('Changes in version 2.8:' in news, 'Upstream source is not release 2.8')
    require('name_is_valid (p_name[reverse_flag])' in source and
            'ptrdiff_t n = p_efake <= i ? p_end - p_ptrn_lines : -i;' in source and
            "make_tempfile (&tmped, 'e', nullptr, O_RDWR | O_BINARY, 0)" in source,
            'Release 2.8 no longer contains the security fixes carried by pkgsrc patches')
    require('ed-style' in test_list and 'r !echo bar' in ed_test,
            'Release 2.8 lost the ed-style security regression')

    version = subprocess.run([str(args.patch_tool), '--version'], capture_output=True,
                             text=True, check=False)
    require(version.returncode == 0 and 'GNU patch 2.8' in version.stdout,
            'Selected patch tool is not the installed GNU patch 2.8')
    with tempfile.TemporaryDirectory(prefix='gnu-patch-provider-', dir=args.work) as temporary:
        work = Path(temporary)
        target = work / 'input.txt'
        target.write_text('before\n')
        diff = work / 'change.diff'
        diff.write_text('--- input.txt\n+++ input.txt\n@@ -1 +1 @@\n-before\n+after\n')
        env = {'PATH': str(args.patch_tool.parent), 'LC_ALL': 'C', 'TZ': 'UTC'}
        result = subprocess.run([str(args.patch_tool), '-p0', '--batch', '--forward',
                                 '--no-backup-if-mismatch', '-i', str(diff)],
                                cwd=work, env=env, capture_output=True, text=True,
                                check=False)
        require(result.returncode == 0 and target.read_text() == 'after\n' and
                not (work / 'input.txt.orig').exists() and not (work / 'input.txt.rej').exists(),
                'The selected GNU patch provider did not apply the source-prep flags')
    print('PASS: GNU patch 2.8 source fixes and source-preparation flags')


if __name__ == '__main__':
    main()
