#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Classify an existing pkgsrc work directory without modifying it.

--explain emits a diagnostic JSON record instead of the shell protocol. It
reports the same checks, not evidence of ABI or complete build compatibility.
"""
import json
import re
import sys
from pathlib import Path

args = sys.argv[1:]
explain = bool(args and args[0] == '--explain')
if explain:
    args = args[1:]
if len(args) != 4:
    sys.exit('cross-bulk: work directory check needs a directory, package base, version, and name')
root, base, version, current = Path(args[0]), *args[1:]
report = {'schema': 'ports-workdir-explanation-v1', 'read_only': True,
          'requested_package': current, 'requested_upstream_version': version,
          'recorded_package': None, 'phase_cookie': None}


def finish(decision, reason, message, next_step):
    if explain:
        report.update(decision=decision, reason=reason, detail=message, next_step=next_step)
        print(json.dumps(report, sort_keys=True))
        sys.exit(0)
    if decision == 'preserve-and-stop':
        sys.exit('cross-bulk: cannot safely reuse work directory: ' + message +
                 '; WRKDIR preserved; ' + next_step)
    print(decision)
    sys.exit(0)


def fail(reason, message, next_step='inspect the retained inputs; explicitly clean only if incompatible'):
    finish('preserve-and-stop', reason, message, next_step)


if root.is_symlink() or not root.is_dir():
    fail('invalid-directory', 'not a real directory')
if not any(root.iterdir()):
    finish('same', 'empty-directory', 'no retained build state', 'continue the ordinary build')
cookie = root / '.extract_done'
if cookie.is_symlink() or not cookie.is_file():
    fail('missing-extract-identity', 'missing extract identity')
old = cookie.read_text(encoding='utf-8').strip()
report.update(recorded_package=old, phase_cookie='.extract_done')
pattern = re.compile(re.escape(base) + r'-([0-9][A-Za-z0-9._+~-]*?)(?:nb[0-9]+)?\Z')
a, b = pattern.fullmatch(old), pattern.fullmatch(current)
if not a or not b or b.group(1) != version:
    fail('unknown-package-identity', 'unknown package identity')
if a.group(1) != version:
    finish('incompatible', 'upstream-version-changed',
           old + ' -> ' + current,
           'ordinary bulk preparation retires this upstream-version work directory')
else:
    latest = old
    # .patch_done contains applied patch paths, not a package identity.
    for name in ('.configure_done', '.build_done', '.install_done', '.package_done'):
        phase = root / name
        if phase.is_symlink() or (phase.exists() and not phase.is_file()):
            report['phase_cookie'] = name
            fail('invalid-phase-identity', 'invalid phase identity ' + name)
        if phase.is_file():
            latest = phase.read_text(encoding='utf-8').strip()
            report.update(recorded_package=latest, phase_cookie=name)
    if latest != current:
        # Selecting a source build does not prove that its objects are
        # incompatible. Preserve them for explicit scoped recovery.
        parsed = pattern.fullmatch(latest)
        if not parsed or parsed.group(1) != version:
            fail('unknown-phase-identity', 'unknown phase identity ' + report['phase_cookie'])
        fail('package-revision-changed',
             'revision changed: ' + latest + ' -> ' + current + ' (' + report['phase_cookie'] + ')',
             'inspect effective source/configuration and dependency changes; '
             'for package metadata only use scoped package/package-install; '
             'otherwise use scoped reconfigure/rebuild recovery; '
             'a revision change alone does not require a clean')
    finish('same', 'package-identity-matches', 'latest recorded package identity matches',
           'continue dependency and normal phase checks; identity alone does not prove compatible inputs')
