#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check actual pkgsrc GNOME backend dependency and upstream Meson selection."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--pkgsrc', type=Path, required=True)
p.add_argument('--archive', type=Path, required=True)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--makeconf', type=Path, required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
recipe = root/'pkgsrc/www/libproxy'
expected = re.search(r'^SHA512 \(' + re.escape(a.archive.name) + r'\) = ([0-9a-f]+)$',
                     (recipe/'distinfo').read_text(), re.M)
if not expected or hashlib.sha512(a.archive.read_bytes()).hexdigest() != expected.group(1):
    raise SystemExit('wrong libproxy source archive')
with tarfile.open(a.archive) as archive:
    options = archive.extractfile('libproxy-0.5.12/meson_options.txt').read().decode()
    meson = archive.extractfile('libproxy-0.5.12/meson.build').read().decode()
    backend = archive.extractfile('libproxy-0.5.12/src/backend/meson.build').read().decode()
if not re.search(r"'config-gnome',\s*type:\s*'boolean',\s*value:\s*true", options):
    raise SystemExit('upstream GNOME option default changed')
if "dependency('gsettings-desktop-schemas', required: get_option('config-gnome'))" not in meson:
    raise SystemExit('upstream GNOME schema dependency changed')
if "get_option('config-gnome')" not in backend:
    raise SystemExit('upstream GNOME backend guard missing')
with tempfile.TemporaryDirectory(prefix='libproxy-gnome-', dir=a.work_parent) as work:
    w = Path(work)
    for entry in a.pkgsrc.iterdir():
        if entry.name != 'www':
            (w/entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    (w/'www').mkdir()
    for entry in (a.pkgsrc/'www').iterdir():
        if entry.name != 'libproxy':
            (w/'www'/entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    shutil.copytree(recipe, w/'www/libproxy', symlinks=True)
    env = os.environ.copy()
    env['MAKECONF'] = str(a.makeconf)
    for selection, enabled in (('', True), ('-gnome -doc -vala', False)):
        result = subprocess.run(
            [str(a.bmake), '-C', str(w/'www/libproxy'), 'PKG_OPTIONS.libproxy='+selection,
             'show-vars', 'VARNAMES=PKG_OPTIONS BUILDLINK_TREE MESON_ARGS'],
            text=True, capture_output=True, env=env, check=True)
        lines = result.stdout.splitlines()
        if len(lines) != 3:
            raise SystemExit('unexpected pkgsrc metadata output')
        options, graph, flags = (set(line.split()) for line in lines)
        if ('gnome' in options) != enabled or ('gsettings-desktop-schemas' in graph) != enabled:
            raise SystemExit('GNOME option and schema dependency disagree')
        if '-Dconfig-gnome=' + str(enabled).lower() not in flags:
            raise SystemExit('GNOME Meson flag disagrees')
        if not {'glib2', 'libduktape', 'curl'} <= graph or any(x.startswith('-Dintrospection=') for x in flags):
            raise SystemExit('other backends or introspection were changed')
print('PASS: libproxy default and GNOME-off real pkgsrc dependency graph')
