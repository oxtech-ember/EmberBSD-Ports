#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""misc/libcdio must use Perl as a build tool only.

perl:run makes a cross build stop ("not supported in cross-compilation") and
adds a runtime dependency although libcdio installs no Perl script.
Usage: libcdio-build-perl.py [--patch /absolute/gpatch]
"""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PATCH = 'profiles/common-build-tools/patches/libcdio-build-perl.patch'
UPSTREAM = ROOT / 'upstream/pkgsrc/misc/libcdio'

parser = argparse.ArgumentParser()
parser.add_argument('--patch', default=shutil.which('gpatch') or 'patch')
args = parser.parse_args()

entries = (ROOT / 'pkgsrc/export.conf').read_text().splitlines()
assert f'patch\t{PATCH}' in entries, 'export.conf does not apply ' + PATCH
for line in (UPSTREAM / 'PLIST').read_text().splitlines():
    assert not re.search(r'perl|\.p[lm]$', line), 'libcdio installs a Perl file: ' + line
with tempfile.TemporaryDirectory() as directory:
    recipe = Path(directory) / 'misc/libcdio'
    recipe.mkdir(parents=True)
    shutil.copy(UPSTREAM / 'Makefile', recipe)
    subprocess.run([args.patch, '-p1', '-F', '0', '-V', 'none', '-s', '-i', str(ROOT / PATCH)],
                   cwd=directory, check=True)
    text = (recipe / 'Makefile').read_text()
tools = ' '.join(re.findall(r'^USE_TOOLS\+=\s*(.*)$', text, re.M)).split()
assert 'perl:run' not in tools and 'perl' in tools, tools
assert re.search(r'^PKGREVISION=\s*\d+$', text, re.M), 'dependency change needs PKGREVISION'
print('PASS: libcdio uses Perl as a build tool only')
