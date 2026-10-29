#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare libopts from the AutoGen distfile without installed AutoGen or Guile.

With --ntp-archive the result is also compared with the libopts tearoff that
NTP ships and installed through NTP's integration helper.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'export', 'git', 'patch', 'archive', 'work-dir'):
    parser.add_argument('--' + name, required=True)
parser.add_argument('--ntp-archive')
a = parser.parse_args()
owner = Path(__file__).with_name('source.py')
base = [sys.executable, '-B', str(owner), '--sdk-source', a.sdk_source,
        '--export', a.export, '--git', a.git, '--patch', a.patch]
# No host prefix, package database, bmake or Guile is selected or reachable.
env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}


def run(*extra, ok=True, archive=a.archive):
    result = subprocess.run([*base, '--archive', str(archive), *map(str, extra)],
                            capture_output=True, text=True, env=env)
    if (result.returncode == 0) != ok:
        raise AssertionError(result.stderr or result.stdout or 'unexpected status')
    return result


with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    tmp = Path(tmp)
    source = tmp / 'libopts'
    run('--output', source)
    for name in ('libopts.c', 'autoopts/options.h', 'autoopts/project.h', 'COPYING.mbsd', 'm4/libopts.m4'):
        assert (source / name).is_file(), name
    # The recipe patchset is part of the payload (patch-ember_libopts_const).
    assert b'argTypes             = { .pzStr = NULL }' in (source / 'autoopts.h').read_bytes()
    assert b'#include "init.c"' in (source / 'libopts.c').read_bytes()
    run('--source', source)
    verify = [sys.executable, '-B', str(owner), '--sdk-source', a.sdk_source, '--git', a.git,
              'verify-source', '--source', str(source), '--patch', a.patch, '--pkgsrc-export', a.export]
    subprocess.run(verify, check=True, capture_output=True, env=env)
    run('--output', source, ok=False)
    # A distfile with the recipe's name but other content is refused.
    bad = tmp / 'bad' / Path(a.archive).name
    bad.parent.mkdir()
    bad.write_bytes(Path(a.archive).read_bytes() + b'\0')
    run('--output', tmp / 'other', archive=bad, ok=False)
    assert not (tmp / 'other').exists()
    # A changed payload no longer matches the distfile and patchset.
    (source / 'unexpected').write_text('changed\n')
    run('--source', source, ok=False)
    assert subprocess.run(verify, capture_output=True, env=env).returncode != 0
    (source / 'unexpected').unlink()
    run('--source', source)
    if a.ntp_archive:
        with tarfile.open(a.ntp_archive) as packed:
            members = [m for m in packed.getmembers() if m.isfile() or m.isdir()]
            packed.extractall(tmp / 'ntp', members=members, filter='data')
        ntp = next((tmp / 'ntp').iterdir())
        shipped = ntp / 'sntp/libopts'
        def files(root):
            return sorted(str(p.relative_to(root)) for p in root.rglob('*')
                          if p.is_file() and p.name != 'emberbsd-prepared-source.json')
        assert files(source) == [n for n in files(shipped) if n != 'Makefile.in'], 'tearoff inventory differs from NTP'
        assert (source / 'libopts.c').read_bytes() == (shipped / 'libopts.c').read_bytes()
        def extra_dist(path):
            text = path.read_text()
            return text[text.index('EXTRA_DIST += \\\n'):]
        assert extra_dist(source / 'Makefile.am') == extra_dist(shipped / 'Makefile.am')
        integration = Path(a.export) / 'pkgsrc/net/ntp4/files/install-libopts-source.py'
        subprocess.run([sys.executable, '-B', str(integration), '--sdk-source', a.sdk_source,
                        '--pkgsrc', str(Path(a.export) / 'pkgsrc'), '--source', str(source),
                        '--ntp', str(ntp)], check=True, capture_output=True, env=env)
        assert (shipped / 'autoopts.h').read_bytes() == (source / 'autoopts.h').read_bytes()
print('AutoGen libopts from distfile: PASS')
