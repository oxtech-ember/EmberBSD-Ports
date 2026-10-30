#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run the Node embedder CJS argument and inspector regressions."""
import argparse
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'work', 'source', 'lock-root'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
if not all(x.is_absolute() for x in (a.sdk_source, a.host_prefix, a.work, a.source, a.lock_root)):
    p.error('all paths must be absolute')
work = a.work.resolve(strict=True)
source = a.source.resolve(strict=True)
if not source.is_relative_to(work):
    p.error('source must belong to selected work')
for name in ('node', 'cctest', 'embedtest'):
    if not (source / 'out/Release' / name).is_file():
        p.error('build node, cctest and the CJS opt-in embedtest fixture first')
sys.path.insert(0, str(a.sdk_source / 'src'))
from emberbsd_sdk.process import ContextLocks, sanitized_environment

env = sanitized_environment()
env['PATH'] = str(a.host_prefix / 'bin') + ':' + str(a.host_prefix / 'sbin')
with ContextLocks([str(a.host_prefix), str(work)], str(a.lock_root), shared=True):
    subprocess.run([str(source / 'out/Release/cctest'), '--gtest_fail_if_no_test_selected',
                    '--gtest_filter=EnvironmentTest.EmbedderCJSExtraArguments'],
                   cwd=source, env=env, timeout=90, check=True)
    subprocess.run([str(source / 'out/Release/node'), str(Path(__file__).with_name('run.cjs')),
                    str(source / 'out/Release/embedtest'), str(source)],
                   cwd=source, env=env, timeout=120, check=True)
