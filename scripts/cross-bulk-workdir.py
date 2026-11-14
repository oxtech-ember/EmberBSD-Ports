#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Classify an existing pkgsrc work directory without modifying it.

Arguments: DIRECTORY PKGBASE VERSION PKGNAME [BUILD_INPUTS]. Prints
fresh (no work directory content), same (the same package identity),
incompatible (another upstream version) or metadata. metadata means that
only the package revision (nbN) changed and that BUILD_INPUTS, the
scripts/cross-bulk-inputs.py digest of the current recipe, equals the
digest that cross-bulk recorded in RECORD after it built these objects: the
objects can be repackaged with the new metadata without compiling them.
Every other revision change stops for an explicit decision.
"""
import re
import sys
from pathlib import Path

RECORD = '.cross-bulk-inputs'
SCHEMA = 'cross-bulk-inputs-v1'

if len(sys.argv) not in (5, 6):
    sys.exit('cross-bulk: work directory check needs a directory, package base, version, and name')
root, base, version, current = Path(sys.argv[1]), *sys.argv[2:5]
inputs = sys.argv[5] if len(sys.argv) == 6 else ''
def fail(message):
    sys.exit('cross-bulk: cannot safely reuse work directory: ' + message +
             '; inspect it and explicitly clean if incompatible')
def recorded():
    path = root / RECORD
    if path.is_symlink() or not path.is_file():
        return ''
    try:
        fields = path.read_text(encoding='utf-8').split()
    except (OSError, UnicodeError):
        return ''
    if len(fields) != 2 or fields[0] != SCHEMA or not re.fullmatch(r'[0-9a-f]{64}', fields[1]):
        return ''
    return fields[1]
if inputs and not re.fullmatch(r'[0-9a-f]{64}', inputs):
    sys.exit('cross-bulk: invalid build-input digest')
if root.is_symlink() or not root.is_dir():
    fail('not a real directory')
if not any(path.name != RECORD for path in root.iterdir()):
    print('fresh')
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
        changed = pattern.fullmatch(latest)
        if changed and changed.group(1) == version and inputs and recorded() == inputs:
            # Only the revision changed, and the recorded recipe inputs of
            # these objects are the current ones.
            print('metadata')
            sys.exit(0)
        # Selecting a source build does not prove that its objects are
        # incompatible. Preserve them for explicit scoped recovery.
        detail = ('build inputs changed since this work directory was built' if inputs and recorded()
                  else 'no recorded build inputs for this work directory')
        fail('revision changed (' + detail + '); explicitly reconfigure/rebuild or use metadata package-install')
    print('same')
