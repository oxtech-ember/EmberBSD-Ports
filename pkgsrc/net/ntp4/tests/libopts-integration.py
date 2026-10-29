#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Test NTP's common libopts source integration without a package install."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'pkgsrc', 'source', 'work-dir'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
script = Path(__file__).resolve().parents[1] / 'files/install-libopts-source.py'
with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    tmp = Path(tmp)
    ntp = tmp / 'ntp'
    original = ntp / 'sntp/libopts'
    original.mkdir(parents=True)
    (ntp / 'sntp/m4').mkdir()
    (ntp / 'sntp/m4/ntp_libevent.m4').write_text('m4\n')
    (ntp / 'aclocal.m4').write_text('top\n')
    (ntp / 'configure.ac').write_text('configure\n')
    (ntp / 'sntp/aclocal.m4').write_text('sntp\n')
    for name in ('Makefile.am', 'Makefile.in'):
        (original / name).write_text('ntp-owned ' + name + '\n')
    (original / 'obsolete-private.c').write_text('old\n')
    cmd = [sys.executable, '-B', str(script), '--sdk-source', str(a.sdk_source),
           '--pkgsrc', str(a.pkgsrc), '--source', str(a.source), '--ntp', str(ntp)]
    subprocess.run(cmd, check=True)
    assert not (original / 'obsolete-private.c').exists()
    for name in ('Makefile.am', 'Makefile.in'):
        assert (original / name).read_text() == 'ntp-owned ' + name + '\n'
    assert not (original / 'emberbsd-prepared-source.json').exists()
    for path in a.source.rglob('*'):
        if path.is_file() and path.name not in ('Makefile.am', 'Makefile.in', 'emberbsd-prepared-source.json'):
            assert (original / path.relative_to(a.source)).read_bytes() == path.read_bytes()
    bad = tmp / 'bad-source'
    shutil.copytree(a.source, bad)
    (bad / 'libopts.c').write_text('changed\n')
    before = (original / 'libopts.c').read_bytes()
    result = subprocess.run([*cmd[:-3], str(bad), '--ntp', str(ntp)], capture_output=True)
    assert result.returncode and (original / 'libopts.c').read_bytes() == before
print('NTP common libopts integration: PASS')
