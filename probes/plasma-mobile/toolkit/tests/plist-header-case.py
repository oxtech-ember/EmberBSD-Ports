#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A case-insensitive staging filesystem merges
# include directories such as KIO/ and kio/. Its file check cannot detect a
# PLIST entry with the wrong directory spelling, and the package then installs
# the header in the wrong directory on a case-sensitive target. ECM installs
# lowercase .h headers in the lowercase directory and CamelCase forwarding
# headers in the CamelCase directory, so a lowercase .h file in a CamelCase
# directory with a lowercase sibling is an error.
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parents[4]
failures = []
checked = 0
for plist in sorted(root.glob('**/recipes/*/*/PLIST')):
    if 'upstream' in plist.relative_to(root).parts:
        continue
    checked += 1
    directories = {}
    for line in plist.read_text().splitlines():
        entry = re.sub(r'^\$\{PLIST\.[^}]+\}', '', line.strip())
        if not entry or entry.startswith('@') or '/' not in entry:
            continue
        directory, name = entry.rsplit('/', 1)
        directories.setdefault(directory, []).append(name)
    for directory, names in directories.items():
        parent, _, leaf = directory.rpartition('/')
        if leaf == leaf.lower() or parent + '/' + leaf.lower() not in directories:
            continue
        for name in names:
            if name.endswith('.h') and name == name.lower():
                failures.append('%s: %s/%s' % (plist.relative_to(root), directory, name))
# pkgsrc generates upstream PLIST files on case-sensitive file systems.
# An entry that differs from the matching upstream entry only in case has
# the merged directory spelling of a case-insensitive staging host.
upstream = root / 'upstream/pkgsrc'
compared = 0
for plist in sorted(root.glob('**/recipes/*/*/PLIST')):
    if 'upstream' in plist.relative_to(root).parts:
        continue
    original = upstream / plist.relative_to(plist.parents[2])
    if not original.is_file():
        continue
    compared += 1
    def entries(path):
        result = set()
        for line in path.read_text(errors='replace').splitlines():
            entry = re.sub(r'^\$\{PLIST\.[^}]+\}', '', line.strip())
            if entry and not entry.startswith('@'):
                result.add(entry)
        return result
    theirs = entries(original)
    folded = {entry.lower(): entry for entry in theirs}
    for entry in sorted(entries(plist)):
        if entry not in theirs and entry.lower() in folded:
            failures.append('%s: %s differs only in case from upstream %s' % (plist.relative_to(root), entry, folded[entry.lower()]))
if compared < 100:
    failures.append('expected at least 100 PLIST files with upstream counterparts, found %d' % compared)
if checked < 100:
    failures.append('expected at least 100 recipe PLIST files, found %d' % checked)
if failures:
    sys.exit('PLIST header case errors:\n' + '\n'.join(failures))
print('PASS: %d recipe PLIST files keep header directory case; %d match upstream case' % (checked, compared))
