#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted) regression for the canonical GNU patch recipe.
"""Check GNU patch 2.8.1 source fixes, CVE-2026-115207 and consumer flags."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


SHA256 = '3240c7959c5347c8ed347e3c4201c0337bf4240d5cf09d68889e58eeaba30e17'
ARCHIVE = 'patch-2.8.1.tar.xz'
VERSION = '2.8.1'


def require(value, message):
    if not value:
        raise AssertionError(message)


def check_source(path):
    data = path.read_bytes()
    require(path.name == ARCHIVE and hashlib.sha256(data).hexdigest() == SHA256,
            'Archive does not match GNU patch 2.8.1 official SHA256')
    with tarfile.open(path, 'r:xz') as archive:
        root = 'patch-' + VERSION + '/'
        def read(name):
            member = archive.getmember(root + name)
            require(member.isfile(), 'Expected regular upstream source member: ' + name)
            return archive.extractfile(member).read().decode('utf-8', errors='strict')
        news = read('NEWS')
        source = read('src/pch.c')
        test_list = read('tests/Makefile.in')
        ed_test = read('tests/ed-style')
        create_delete = read('tests/create-delete')
    require(news.startswith('Changes in version 2.8.1:') and
            'Prevent creation of out-of-tree files (CVE-2026-115207).' in news,
            'Upstream source is not security release 2.8.1')
    require('name_is_valid (p_name[reverse_flag])' in source and
            'ptrdiff_t n = p_efake <= i ? p_end - p_ptrn_lines : -i;' in source and
            "make_tempfile (&tmped, 'e', nullptr, O_RDWR | O_BINARY, 0)" in source,
            'Release 2.8.1 no longer contains the security fixes carried by pkgsrc patches')
    require('if (i0 != NONE\n\t\t&& name_is_valid (p_name[i0])\n' in source,
            'Release 2.8.1 lacks the CVE-2026-115207 reverse-create name check')
    require('ed-style' in test_list and 'r !echo bar' in ed_test,
            'Release 2.8.1 lost the ed-style security regression')
    require('create-delete' in test_list and
            'Reverse-applying a patch should not' in create_delete,
            'Release 2.8.1 lost the upstream out-of-tree creation regression')


def run_patch(tool, cwd, *arguments):
    env = {'PATH': str(tool.parent), 'LC_ALL': 'C', 'TZ': 'UTC'}
    return subprocess.run([str(tool), *arguments], cwd=cwd, env=env,
                          capture_output=True, text=True, check=False)


def check_reverse_delete(tool, scratch):
    # CVE-2026-115207: when a patch deletes a missing file, batch mode assumes
    # -R and 2.8 recreated it at an unchecked absolute path outside the tree
    # (absolute-auto fails on 2.8).  The other cases guard related name checks.
    cases = (
        ('absolute-auto', True, ('-p0', '-t')),
        ('absolute-reverse', True, ('-p0', '-R', '--batch')),
        ('dotdot-auto', False, ('-p0', '-t')),
        ('dotdot-reverse', False, ('-p0', '-R', '--batch')),
    )
    for label, absolute, flags in cases:
        with tempfile.TemporaryDirectory(prefix='gnu-patch-cve-', dir=scratch) as temporary:
            base = Path(temporary).resolve()
            tree = base / 'tree'
            tree.mkdir()
            outside = base / 'outside.txt'
            name = str(tree / '..' / 'outside.txt') if absolute else '../outside.txt'
            diff = base / 'delete.diff'
            diff.write_text('--- %s\t2025-01-01 12:00:00.000000000 +0000\n'
                            '+++ %s\t1970-01-01 00:00:00.000000000 +0000\n'
                            '@@ -1 +0,0 @@\n-data\n' % (name, name))
            result = run_patch(tool, tree, *flags, '-i', str(diff))
            output = result.stdout + result.stderr
            require(not outside.exists() and not os.path.lexists(outside),
                    '%s: reverse-applied deletion wrote outside the tree '
                    '(CVE-2026-115207)' % label)
            require(sorted(p.name for p in base.iterdir()) == ['delete.diff', 'tree'] and
                    not any(tree.iterdir()),
                    '%s: unexpected files created by refused patch' % label)
            require(result.returncode == 1 and
                    'Ignoring potentially dangerous file name ' + name in output,
                    '%s: patch did not reject the out-of-tree name: rc=%d\n%s'
                    % (label, result.returncode, output))


def check_source_prep(tool, scratch):
    with tempfile.TemporaryDirectory(prefix='gnu-patch-provider-', dir=scratch) as temporary:
        work = Path(temporary)
        target = work / 'input.txt'
        target.write_text('before\n')
        diff = work / 'change.diff'
        diff.write_text('--- input.txt\n+++ input.txt\n@@ -1 +1 @@\n-before\n+after\n')
        result = run_patch(tool, work, '-p0', '--batch', '--forward',
                           '--no-backup-if-mismatch', '-i', str(diff))
        require(result.returncode == 0 and target.read_text() == 'after\n' and
                not (work / 'input.txt.orig').exists() and
                not (work / 'input.txt.rej').exists(),
                'The selected GNU patch provider did not apply the source-prep flags')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path,
                        help='verified GNU patch distfile (required unless --binary-only)')
    parser.add_argument('--patch-tool', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--binary-only', action='store_true',
                        help='skip version and source checks; run behavior checks only')
    args = parser.parse_args()
    require(args.patch_tool.is_absolute() and args.patch_tool.is_file() and
            os.access(args.patch_tool, os.X_OK),
            'Use the installed executable GNU patch provider')
    require(args.work.is_absolute() and args.work.is_dir(),
            'Use an existing scratch directory inside the workspace')
    if not args.binary_only:
        require(args.archive is not None and args.archive.is_absolute() and
                args.archive.is_file(), 'Use the verified absolute GNU patch archive')
        check_source(args.archive)
        version = run_patch(args.patch_tool, args.work, '--version')
        require(version.returncode == 0 and
                version.stdout.splitlines()[:1] == ['GNU patch ' + VERSION],
                'Selected patch tool is not the installed GNU patch ' + VERSION)
    check_reverse_delete(args.patch_tool, args.work)
    check_source_prep(args.patch_tool, args.work)
    print('PASS: GNU patch %s source fixes, CVE-2026-115207 and source-preparation flags'
          % ('behavior' if args.binary_only else VERSION))


if __name__ == '__main__':
    main()
