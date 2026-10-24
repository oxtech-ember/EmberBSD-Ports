#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted regression for the common recipe export.
"""Run the actual exporter against a small upstream archive fixture."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pkgsrc', required=True, type=Path)
parser.add_argument('--work-parent', required=True, type=Path)
a = parser.parse_args()
recipe = Path(__file__).resolve().parents[1]
ports = recipe.parents[2]
with tempfile.TemporaryDirectory(prefix='editline-export-', dir=a.work_parent) as temporary:
    root = Path(temporary)
    fixture = root / 'ports'
    upstream = fixture / 'upstream/pkgsrc'
    shutil.copytree(recipe, fixture / 'pkgsrc/devel/editline')
    for relative in ('scripts/prepare-pkgsrc.py', 'pkgsrc/defaults.mk.conf',
                     'profiles/common-build-tools/patches/current-automake-tools.patch'):
        target = fixture / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ports / relative, target)
    (fixture / 'pkgsrc/replaces').write_text('devel/editline\n')
    (fixture / 'pkgsrc/export.conf').write_text(
        'patch\tprofiles/common-build-tools/patches/current-automake-tools.patch\n'
        'file\tpkgsrc/defaults.mk.conf\tEMBERBSD-DEFAULTS-MK.CONF\n')
    for relative in ('devel/Makefile', 'devel/editline/Makefile', 'mk/tools/automake.mk'):
        target = upstream / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(a.pkgsrc / relative, target)
    old = upstream / 'devel/editline/old-provider'
    old.write_text('remove the old provider completely\n')
    environment = dict(os.environ, FAKE_ARCHIVE=str(upstream), FAKE_MATCH='1', TMPDIR=str(root))
    destination = root / 'export'
    done = subprocess.run([sys.executable, '-B', str(ports / 'scripts/tests/export-fixture.py'), str(fixture), str(destination)],
                          text=True, capture_output=True, env=environment, timeout=60)
    assert done.returncode == 0, done.stderr + done.stdout
    exported = destination / 'devel/editline'
    assert not (exported / 'old-provider').exists()
    source_files = {p.relative_to(recipe):p.read_bytes() for p in recipe.rglob('*') if p.is_file()}
    actual_files = {p.relative_to(exported):p.read_bytes() for p in exported.rglob('*') if p.is_file()}
    assert actual_files == source_files, 'The common export changed or omitted recipe files'
    assert (destination / 'EMBERBSD-DEFAULTS-MK.CONF').read_bytes() == (ports / 'pkgsrc/defaults.mk.conf').read_bytes()
    assert 'devel/editline' in (ports / 'pkgsrc/replaces').read_text().splitlines()
    assert not (ports / 'profiles/shells/recipes/devel/editline').exists()
    assert '.include "${.PARSEDIR}/EMBERBSD-DEFAULTS-MK.CONF"' in (ports / 'profiles/shells/mk.conf').read_text()
print('PASS: common export replaces the old provider and preserves every canonical recipe byte')
