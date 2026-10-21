#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross KDE packages install Qt metatypes
# relative to the CMake prefix. Their exported targets name the files below
# the consumer's buildlink prefix, so each provider must buildlink them.
import pathlib
import re
import sys

toolkit = pathlib.Path(__file__).resolve().parents[1]
recipes = toolkit / 'recipes'
shared = toolkit / 'shared/meta-pkgs/kde'
failures = []
for name in ('kf6.mk', 'plasma6.mk', 'applications.mk'):
    text = (shared / name).read_text()
    if '-DKDE_INSTALL_QTMETATYPESDIR=qt6/metatypes' not in text:
        failures.append(name + ': relative metatypes directory is not selected')
checked = 0
for makefile in sorted(recipes.glob('*/*/Makefile')):
    recipe = makefile.parent
    if not re.search(r'meta-pkgs/kde/(kf6|plasma6|applications)\.mk', makefile.read_text()):
        continue
    plist = recipe / 'PLIST'
    files = [line.strip() for line in plist.read_text().splitlines()
             if re.match(r'^(\$\{PLIST\.[^}]+\})?qt6/metatypes/', line.strip())] if plist.exists() else []
    if not files:
        continue
    checked += 1
    buildlink = recipe / 'buildlink3.mk'
    if not buildlink.exists():
        failures.append(str(recipe.relative_to(recipes)) + ': installs metatypes without buildlink3.mk')
        continue
    text = buildlink.read_text()
    match = re.search(r'^BUILDLINK_PKGSRCDIR\.([^?\s]+)\?=', text, re.M)
    if not match:
        failures.append(str(recipe.relative_to(recipes)) + ': no BUILDLINK_PKGSRCDIR')
        continue
    linked = set(re.findall(r'^BUILDLINK_FILES\.' + re.escape(match[1]) + r'\+=\s*(\S+)\s*$', text, re.M))
    for entry in files:
        path = re.sub(r'^\$\{PLIST\.[^}]+\}', '', entry)
        if path not in linked:
            failures.append(str(recipe.relative_to(recipes)) + ': ' + path + ' is not buildlinked')
if checked < 7:
    failures.append('expected at least seven KDE metatypes providers, found %d' % checked)
if failures:
    sys.exit('\n'.join(failures))
print('PASS: %d cross KDE metatypes providers buildlink every installed metatypes file' % checked)
