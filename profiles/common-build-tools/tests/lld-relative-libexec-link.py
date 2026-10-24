#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run the real lld post-install target and check its libexec link stays in the prefix."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
if len(sys.argv) != 5:
    raise SystemExit('Use EXPORTED_PKGSRC MAKECONF BMAKE NEW_WORK')
export, makeconf, bmake = map(lambda value: Path(value).resolve(strict=True), sys.argv[1:4])
work = Path(sys.argv[4]).absolute()
work.mkdir()
root = Path(__file__).resolve().parents[3]
tree = work / 'pkgsrc'
(tree / 'devel').mkdir(parents=True)
for entry in export.iterdir():
    if entry.name != 'devel':
        (tree / entry.name).symlink_to(entry)
for entry in (export / 'devel').iterdir():
    if entry.name == 'lld':
        shutil.copytree(root / 'pkgsrc/devel/lld', tree / 'devel/lld')
    else:
        (tree / 'devel' / entry.name).symlink_to(entry)
rows = []
# A staged package and a direct prefix install both create the same link.
for name, destdir, prefix in (('staged', work / 'stage', '/opt/ember-lld'),
                              ('direct', None, str(work / 'direct/prefix'))):
    top = Path(str(destdir) + prefix) if destdir else Path(prefix)
    (top / 'bin').mkdir(parents=True)
    (top / 'libexec/lld').mkdir(parents=True)
    (top / 'bin/lld').write_text('Labelled lld image fixture.\n')
    command = [str(bmake), '-C', str(tree / 'devel/lld'), 'MAKECONF=' + str(makeconf),
               'WRKOBJDIR=' + str(work / 'objects'), 'PKG_DBDIR=' + str(work / 'pkgdb'),
               'PREFIX=' + prefix, 'DESTDIR=' + (str(destdir) if destdir else ''), 'post-install']
    result = subprocess.run(command, capture_output=True, text=True)
    (work / (name + '.log')).write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    link = top / 'libexec/lld/ld'
    target = os.readlink(link)
    rows.append(dict(case=name, argv=command, link=str(link), target=target))
    (work / 'receipt.json').write_text(json.dumps(rows, indent=2) + '\n')
    assert not os.path.isabs(target), name + ': absolute link escapes a relocated prefix: ' + target
    assert link.resolve(strict=True) == (top / 'bin/lld').resolve(strict=True), name + ': ' + target
print('PASS: real devel/lld post-install keeps libexec/lld/ld relative for staged and direct prefixes')
print('SCOPE: post-install target only; no compiler or linker ran')
