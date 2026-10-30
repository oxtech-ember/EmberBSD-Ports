#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run selected Node/V8 cache-observation regressions."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
p = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'work', 'cctest', 'lock-root'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
if not all(x.is_absolute() for x in (a.sdk_source, a.host_prefix, a.work, a.cctest, a.lock_root)):
    p.error('all selected paths must be absolute')
work = a.work.resolve(strict=True)
test = a.cctest.resolve(strict=True)
if not test.is_relative_to(work) or not test.is_file() or not os.access(test, os.X_OK):
    p.error('cctest must be an executable within the selected work')
sys.path.insert(0, str(a.sdk_source / 'src'))
from emberbsd_sdk.process import ContextLocks, sanitized_environment
env = sanitized_environment()
env['PATH'] = str(a.host_prefix / 'bin') + ':' + str(a.host_prefix / 'sbin')
with ContextLocks([str(a.host_prefix), str(work)], str(a.lock_root), shared=True):
    subprocess.run([str(test), '--gtest_fail_if_no_test_selected',
                    '--gtest_filter=EnvironmentTest.V8WrappedFunctionCacheDetails:BuiltinCacheTest.CustomParametersCacheStatus:EnvironmentTest.WorkerBuiltinCacheHitAndReject'],
                   cwd=work, env=env, timeout=120, check=True)
