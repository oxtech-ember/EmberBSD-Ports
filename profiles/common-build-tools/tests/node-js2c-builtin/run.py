#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Prepare a js2c test input or run its compiled Node preload tests."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('action', choices=('prepare', 'run'))
for name in ('sdk-source', 'host-prefix', 'work', 'lock-root'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--js2c', type=Path)
p.add_argument('--tool-work', type=Path, help='selected Node build work containing js2c')
p.add_argument('--cctest', type=Path)
a = p.parse_args()
if not all(x.is_absolute() for x in (a.sdk_source, a.host_prefix, a.work, a.lock_root)):
    p.error('selected paths must be absolute')
work = a.work.resolve(strict=True)
sys.path.insert(0, str(a.sdk_source / 'src'))
from emberbsd_sdk.process import ContextLocks, sanitized_environment

env = sanitized_environment()
env['PATH'] = str(a.host_prefix / 'bin') + ':' + str(a.host_prefix / 'sbin')
here = Path(__file__).resolve().parent
if a.action == 'prepare':
    if not a.js2c or not a.js2c.is_absolute():
        p.error('prepare requires the absolute selected js2c executable')
    if a.tool_work and not a.tool_work.is_absolute():
        p.error('tool work must be absolute')
    js2c = a.js2c.resolve(strict=True)
    host = a.host_prefix.resolve(strict=True)
    tool_work = a.tool_work.resolve(strict=True) if a.tool_work and a.tool_work.is_absolute() else None
    if (not js2c.is_file() or not os.access(js2c, os.X_OK) or
        not (js2c.is_relative_to(host) or (tool_work and js2c.is_relative_to(tool_work)))):
        p.error('js2c must be executable within the host prefix or selected tool work')
    shared_roots = (host,) if tool_work is None else (host, tool_work)
    if any(work.is_relative_to(root) or root.is_relative_to(work) for root in shared_roots):
        p.error('fixture work must not overlap the shared tool work or host prefix')
    fixture = work / 'internal/electron/js2c/node_init.js'
    with ContextLocks([str(host), str(tool_work or host)], str(a.lock_root), shared=True), ContextLocks([str(work)], str(a.lock_root)):
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_bytes((here / 'node_init.js').read_bytes())
        subprocess.run([str(js2c), str(work / 'electron_natives.cc'),
                        'internal/electron/js2c/node_init.js', '--only-js', '--root', str(work),
                        '--process-lifetime'], cwd=work, env=env, check=True)
    print('Generated test source:', work / 'electron_natives.cc')
    print('GYP input:', here / 'fixture.gypi')
else:
    if not a.cctest or not a.cctest.is_absolute() or not a.cctest.resolve(strict=True).is_relative_to(work):
        p.error('run requires the selected cctest within work')
    if not a.cctest.is_file() or not os.access(a.cctest, os.X_OK):
        p.error('selected cctest must be executable')
    with ContextLocks([str(a.host_prefix), str(work)], str(a.lock_root), shared=True):
        subprocess.run([str(a.cctest), '--gtest_fail_if_no_test_selected',
                        '--gtest_filter=EnvironmentTest.EmbedderPreloadOrdinaryESMMainOnly:EnvironmentTest.EmbedderPreloadOrdinaryESMAndWorker'],
                       cwd=work, env=env, timeout=120, check=True)
