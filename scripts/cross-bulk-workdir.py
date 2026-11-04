#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Classify an existing pkgsrc work directory without modifying it."""
import re
import sys
from pathlib import Path

root, base, version, current = Path(sys.argv[1]), *sys.argv[2:]
def fail(message):
    sys.exit('cross-bulk: cannot safely reuse work directory: ' + message +
             '; inspect it and explicitly clean if incompatible')
if root.is_symlink() or not root.is_dir():
    fail('not a real directory')
if not any(root.iterdir()):
    print('same')
    sys.exit(0)
cookie = root / '.extract_done'
if cookie.is_symlink() or not cookie.is_file():
    fail('missing extract identity')
old = cookie.read_text(encoding='utf-8').strip()
pattern = re.compile(re.escape(base) + r'-([0-9][A-Za-z0-9._+~-]*?)(?:nb[0-9]+)?\Z')
a, b = pattern.fullmatch(old), pattern.fullmatch(current)
if not a or not b or b.group(1) != version:
    fail('unknown package identity')
if a.group(1) != version:
    print('incompatible')
else:
    latest = old
    # .patch_done contains applied patch paths, not a package identity.
    for name in ('.configure_done', '.build_done', '.install_done', '.package_done'):
        phase = root / name
        if phase.is_symlink() or (phase.exists() and not phase.is_file()):
            fail('invalid phase identity ' + name)
        if phase.is_file():
            latest = phase.read_text(encoding='utf-8').strip()
    if latest != current:
        fail('revision changed; explicitly reconfigure/rebuild or use metadata package-install')
    print('same')
