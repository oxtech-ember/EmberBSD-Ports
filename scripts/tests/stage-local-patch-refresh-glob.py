#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check bounded unselected substitution globs and unsafe matches."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', required=True, type=Path)
args = parser.parse_args()
sys.path.insert(0, str(args.sdk_source / 'src'))
from emberbsd_sdk import paths
from emberbsd_sdk.errors import SDKError
spec = importlib.util.spec_from_file_location('refresh', Path(__file__).resolve().parents[1] / 'stage-local-patch-refresh.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='subst-glob-test-') as temp:
    base = Path(temp)
    roots = [base / name for name in ('old', 'new', 'live')]
    names = ['catalog.xml.in', 'dbus-faq.xml', 'dbus-specification.xml', 'dbus-test-plan.xml',
             'dbus-tutorial.xml'] + [f'dbus-{name}.1.xml.in' for name in
             ('cleanup-sockets', 'daemon', 'launch', 'monitor', 'run-session', 'send',
              'test-tool', 'update-activation-environment', 'uuidgen')]
    for root in roots:
        (root / 'doc').mkdir(parents=True)
        for name in names:
            (root / 'doc' / name).write_text('source\n')
    (roots[2] / 'doc/generated.xml').write_text('generated\n')
    (roots[2] / 'object.o').write_bytes(b'preserved')
    mtime = (roots[2] / 'object.o').stat().st_mtime_ns
    module.unselected_subst_pattern(paths, roots, 'doc/*.xml*', {'doc/meson.build', 'missing.c'})
    module.unselected_subst_pattern(paths, roots, 'doc/dbus-?aq.xml', set())
    assert (roots[2] / 'object.o').stat().st_mtime_ns == mtime
    def rejected(pattern, changed=()):
        try:
            module.unselected_subst_pattern(paths, roots, pattern, set(changed))
        except (ValueError, OSError, SDKError) as exc:
            return str(exc)
        raise AssertionError('accepted unsafe pattern: ' + pattern)
    assert 'changed source' in rejected('doc/*.xml*', ['doc/future.xml'])
    (roots[2] / 'doc/.hidden.xml').symlink_to('dbus-faq.xml')
    module.unselected_subst_pattern(paths, roots, 'doc/*.xml', {'doc/.hidden.xml'})
    assert 'changed source' in rejected('doc/.*.xml', ['doc/.hidden.xml'])
    assert 'regular substitution match' in rejected('doc/.*.xml')
    (roots[2] / 'doc/.hidden.xml').unlink()
    for pattern in ('/doc/*.xml', '../doc/*.xml', 'doc/**/file', 'doc/[abc].xml', 'doc//*.xml'):
        assert 'unsupported substitution' in rejected(pattern)
    (roots[2] / 'doc/link.xml').symlink_to('dbus-faq.xml')
    assert 'regular substitution match' in rejected('doc/*.xml')
    (roots[2] / 'doc/link.xml').unlink()
    (roots[2] / 'doc/folder.xml').mkdir()
    assert 'regular substitution match' in rejected('doc/*.xml')
    (roots[2] / 'doc/folder.xml').rmdir()
    os.mkfifo(roots[2] / 'doc/pipe.xml')
    assert 'regular substitution match' in rejected('doc/*.xml')
    (roots[2] / 'doc/pipe.xml').unlink()
    (roots[2] / 'alias').symlink_to('doc', target_is_directory=True)
    assert 'unsafe substitution ancestor' in rejected('a*/*.xml')
    (roots[2] / 'alias').unlink()
    # A regular file matching an intermediate wildcard is not an ancestor.
    (roots[2] / 'artifact').write_text('not a directory')
    module.unselected_subst_pattern(paths, roots, 'a*/*.xml', set())
print('PASS: bounded unselected SUBST glob paths, matches and safety')
