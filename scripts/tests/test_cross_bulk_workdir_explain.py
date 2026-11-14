#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check diagnostic/shell parity without changing retained state."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

classifier = Path(__file__).resolve().parents[1] / 'cross-bulk-workdir.py'
with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp) / 'work'
    work.mkdir()
    digest = 'a' * 64
    record = work / '.cross-bulk-inputs'
    def check(decision, reason, *, inputs=None, current='demo-1.0nb2', version='1.0'):
        paths = sorted(work.iterdir())
        saved = {p: (p.lstat().st_ino, p.lstat().st_mtime_ns,
                      p.readlink() if p.is_symlink() else p.read_bytes()) for p in paths}
        argv = [str(work), 'demo', version, current] + ([] if inputs is None else [inputs])
        shell = subprocess.run([sys.executable, str(classifier), *argv], text=True, capture_output=True)
        diagnostic = subprocess.run([sys.executable, str(classifier), '--explain', *argv], text=True, capture_output=True)
        assert diagnostic.returncode == 0, diagnostic.stderr
        report = json.loads(diagnostic.stdout)
        assert report['decision'] == decision and report['reason'] == reason, report
        assert report['read_only'] and report['dependency_checks'] == 'not-performed'
        assert report['schema'] == 'ports-workdir-explanation-v1'
        assert report['inputs_record'] == {'fresh': 'write', 'incompatible': 'write', 'same': 'same',
                                           'metadata': 'keep', 'preserve-and-stop': 'unchanged'}[decision]
        assert (shell.returncode != 0) == (decision == 'preserve-and-stop'), shell
        if decision != 'preserve-and-stop':
            assert shell.stdout.strip() == decision
        assert sorted(work.iterdir()) == paths
        assert saved == {p: (p.lstat().st_ino, p.lstat().st_mtime_ns,
                             p.readlink() if p.is_symlink() else p.read_bytes()) for p in paths}
        return report
    check('fresh', 'empty-directory')
    record.write_text('cross-bulk-inputs-v1 ' + digest + '\n')
    assert check('fresh', 'empty-directory', inputs=digest)['build_inputs_recorded'] is None
    (work / 'kept.o').write_bytes(b'object')
    check('preserve-and-stop', 'missing-extract-identity')
    (work / '.extract_done').write_text('demo-1.0nb1\n')
    for inputs in (None, ''):
        r = check('preserve-and-stop', 'package-revision-changed', inputs=inputs)
        assert not r['build_inputs_supplied'] and r['build_inputs_match'] is None
    r = check('metadata', 'revision-only-inputs-match', inputs=digest)
    assert r['build_inputs_match'] is True and 'dependency' in r['next_step']
    r = check('preserve-and-stop', 'package-revision-changed', inputs='b' * 64)
    assert r['build_inputs_match'] is False
    check('same', 'package-identity-matches', current='demo-1.0nb1', inputs=digest)
    check('incompatible', 'upstream-version-changed', current='demo-2.0', version='2.0', inputs=digest)
    for mode in ([], ['--explain']):
        invalid = subprocess.run([sys.executable, str(classifier), *mode, str(work), 'demo', '1.0', 'demo-1.0nb2', 'invalid'], capture_output=True, text=True)
        assert invalid.returncode != 0 and 'invalid build-input digest' in invalid.stderr
        assert not invalid.stdout
    for content in ('bad', 'cross-bulk-inputs-v0 ' + digest, 'cross-bulk-inputs-v1 ' + digest + ' extra'):
        record.write_text(content)
        assert not check('preserve-and-stop', 'package-revision-changed', inputs=digest)['build_inputs_recorded']
    record.unlink()
    outside = Path(tmp) / 'outside'
    outside.write_text('cross-bulk-inputs-v1 ' + digest)
    record.symlink_to(outside)
    assert not check('preserve-and-stop', 'package-revision-changed', inputs=digest)['build_inputs_recorded']
    record.unlink()
    check('preserve-and-stop', 'package-revision-changed', inputs=digest)
    (work / '.package_done').write_text('not an identity')
    r = check('preserve-and-stop', 'unknown-phase-identity', inputs=digest)
    assert r['phase_cookie'] == '.package_done' and r['recorded_package'] == 'not an identity'
    (work / '.package_done').unlink()
    (work / '.build_done').symlink_to(outside)
    check('preserve-and-stop', 'invalid-phase-identity', inputs=digest)
print('PASS: shell/JSON decisions agree; digest diagnostics preserve files and dependency gates')
