#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Classify an existing pkgsrc work directory without modifying it.

Arguments: DIRECTORY PKGBASE VERSION PKGNAME [BUILD_INPUTS]. Prints
fresh (no work directory content), same (matching package identity and recorded inputs),
incompatible (another upstream version) or metadata. metadata means that
only the package revision (nbN) changed and that BUILD_INPUTS, the
scripts/cross-bulk-inputs.py digest of the current recipe, equals the
digest that cross-bulk recorded in RECORD after it built these objects: the
objects can be repackaged with the new metadata without compiling them.
Every other revision change stops for an explicit decision.

--explain prints the same decision as read-only JSON, with the handling of
the build-input record that a bulk build then applies (inputs_record):
write (the objects are compiled from an empty or retired work directory and
a successful build writes the record), same (a present record is kept only
when it equals the current digest; none is written), keep (the metadata path
keeps the matching record) or unchanged (the build stops). A bulk build still
checks the dependency lists afterwards; --explain does not.
"""
import json
import re
import sys
from pathlib import Path

RECORD = '.cross-bulk-inputs'
START = '.cross-bulk-start-inputs'
SCHEMA = 'cross-bulk-inputs-v1'

args = sys.argv[1:]
explain = bool(args and args[0] == '--explain')
if explain:
    args = args[1:]
if len(args) not in (4, 5):
    sys.exit('cross-bulk: work directory check needs a directory, package base, version, and name')
root, base, version, current = Path(args[0]), *args[1:4]
inputs = args[4] if len(args) == 5 else ''
report = {'schema': 'ports-workdir-explanation-v1', 'read_only': True,
          'requested_package': current, 'requested_upstream_version': version,
          'recorded_package': None, 'phase_cookie': None,
          'build_inputs_supplied': bool(inputs), 'build_inputs_recorded': None,
          'build_inputs_started': None, 'build_inputs_match': None, 'dependency_checks': 'not-performed'}


# How a bulk build handles WRKDIR/RECORD after each decision (prepare_wrkdir
# and record_build_inputs in cross-bulk.sh).
INPUTS_RECORD = {'fresh': 'write', 'incompatible': 'write', 'same': 'same',
                 'metadata': 'keep', 'preserve-and-stop': 'unchanged'}


def finish(decision, reason, message, next_step):
    if explain:
        report.update(decision=decision, reason=reason, detail=message, next_step=next_step,
                      inputs_record=INPUTS_RECORD[decision])
        print(json.dumps(report, sort_keys=True))
        sys.exit(0)
    if decision == 'preserve-and-stop':
        sys.exit('cross-bulk: cannot safely reuse work directory: ' + message +
                 '; WRKDIR preserved; ' + next_step)
    print(decision)
    sys.exit(0)


def fail(message, reason='package-revision-changed'):
    finish('preserve-and-stop', reason, message,
           'inspect effective inputs and dependencies; explicitly reconfigure/rebuild '
           'or use scoped metadata package-install; clean only if incompatible')


def recorded(filename):
    path = root / filename
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
    fail('not a real directory', 'invalid-directory')
if not any(path.name not in (START, RECORD, '.cross-bulk-providers') for path in root.iterdir()):
    finish('fresh', 'empty-directory', 'no retained build state', 'continue the ordinary build')
cookie = root / '.extract_done'
if cookie.is_symlink() or not cookie.is_file():
    fail('missing extract identity', 'missing-extract-identity')
old = cookie.read_text(encoding='utf-8').strip()
report.update(recorded_package=old, phase_cookie='.extract_done')
stored_inputs = recorded(RECORD)
started_inputs = recorded(START)
known_inputs = stored_inputs or started_inputs
report.update(build_inputs_recorded=bool(stored_inputs), build_inputs_started=bool(started_inputs),
              build_inputs_match=(known_inputs == inputs) if known_inputs and inputs else None)
pattern = re.compile(re.escape(base) + r'-([0-9][A-Za-z0-9._+~-]*?)(?:nb[0-9]+)?\Z')
a, b = pattern.fullmatch(old), pattern.fullmatch(current)
if not a or not b or b.group(1) != version:
    fail('unknown package identity', 'unknown-package-identity')
if a.group(1) != version:
    finish('incompatible', 'upstream-version-changed', old + ' -> ' + current,
           'ordinary bulk preparation retires this upstream-version work directory')
else:
    latest = old
    # .patch_done contains applied patch paths, not a package identity.
    for name in ('.configure_done', '.build_done', '.install_done', '.package_done'):
        phase = root / name
        if phase.is_symlink() or (phase.exists() and not phase.is_file()):
            report['phase_cookie'] = name
            fail('invalid phase identity ' + name, 'invalid-phase-identity')
        if phase.is_file():
            latest = phase.read_text(encoding='utf-8').strip()
            report.update(recorded_package=latest, phase_cookie=name)
    if latest != current:
        changed = pattern.fullmatch(latest)
        if changed and changed.group(1) == version and inputs and stored_inputs == inputs:
            # Only the revision changed, and the recorded recipe inputs of
            # these objects are the current ones.
            finish('metadata', 'revision-only-inputs-match', 'revision changed with matching recorded build inputs',
                   'continue dependency checks; only then repackage metadata from retained objects')
        # Selecting a source build does not prove that its objects are
        # incompatible. Preserve them for explicit scoped recovery.
        if not changed or changed.group(1) != version:
            fail('unknown phase identity ' + report['phase_cookie'], 'unknown-phase-identity')
        if not stored_inputs:
            detail = 'no recorded build inputs for this work directory'
        elif not inputs:
            detail = 'current build inputs unavailable to compare with the record'
        else:
            detail = 'build inputs changed since this work directory was built'
        fail('revision changed (' + detail + ')')
    if inputs and (stored_inputs or started_inputs) and inputs != (stored_inputs or started_inputs):
        finish('incompatible', 'build-inputs-changed', 'same identity, different recorded build inputs',
               'ordinary build restarts this package from the changed inputs')
    if not inputs or not (stored_inputs or started_inputs):
        fail('no matching build-input evidence for this package identity', 'unknown-build-inputs')
    finish('same', 'package-identity-matches', 'latest recorded package identity matches',
           'continue dependency and normal phase checks; identity alone does not prove compatible inputs')
