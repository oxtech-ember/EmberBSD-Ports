#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check rejected identities and interrupted compatible phase updates."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', required=True, type=Path)
args = parser.parse_args()
sys.dont_write_bytecode = True
sys.path.insert(0, str(args.sdk_source / 'src'))
from emberbsd_sdk import paths

spec = importlib.util.spec_from_file_location(
    'refresh', Path(__file__).resolve().parents[1] / 'stage-local-patch-refresh.py')
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)

with tempfile.TemporaryDirectory() as directory:
    work = Path(directory).resolve()
    cookies = [work / name for name in ('.extract_done', '.configure_done')]
    for cookie in cookies:
        cookie.write_text('demo-1nb1\n')
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in cookies}
    for version, current in [('2', 'demo-2'), ('1', 'foreign-1')]:
        try:
            refresh.phase_identities(paths, work, 'demo', version, current)
        except ValueError:
            pass
        else:
            raise AssertionError('incompatible identity was accepted')
        assert {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in cookies} == before

    identities = refresh.phase_identities(paths, work, 'demo', '1', 'demo-1nb2')
    replace = os.replace
    def interrupt_second(source, destination):
        if Path(destination).name == '.configure_done':
            raise OSError('injected interruption between phase updates')
        return replace(source, destination)
    with patch.object(refresh.os, 'replace', side_effect=interrupt_second):
        try:
            refresh.refresh_phase_identities(paths, work, identities, 'demo-1nb2')
        except OSError as error:
            assert 'injected interruption' in str(error)
        else:
            raise AssertionError('interruption was not exercised')
    assert cookies[0].read_text() == 'demo-1nb2\n'
    assert cookies[1].read_text() == 'demo-1nb1\n'
    refresh.refresh_phase_identities(paths, work, identities, 'demo-1nb2')
    assert all(p.read_text() == 'demo-1nb2\n' for p in cookies)
    assert all(p.stat().st_mtime_ns == before[p.name][1] for p in cookies)
    assert not list(work.glob('.phase-identity-*'))

    # configure-clean invalidates the phase; retry must not recreate it.
    cookies[1].unlink()
    refresh.refresh_phase_identities(paths, work, identities, 'demo-1nb2')
    assert not cookies[1].exists()
    assert not (work / '.build_done').exists()

print('PASS: incompatible identities reject; interrupted metadata update resumes without replaying phases')
