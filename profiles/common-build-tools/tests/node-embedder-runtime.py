#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise Node ESM callbacks and worker-isolate teardown with a selected build."""
import argparse
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'node', 'cctest', 'source', 'work', 'lock-root'):
    parser.add_argument('--' + name, required=True, type=Path)
a = parser.parse_args()
if not all(p.is_absolute() for p in (a.sdk_source, a.host_prefix, a.node, a.cctest, a.source, a.work, a.lock_root)):
    parser.error('all selected paths must be absolute')
if not all(p.resolve().is_relative_to(a.work.resolve()) for p in (a.node, a.cctest, a.source)):
    parser.error('Node, cctest and source must belong to the selected build work')
if not a.node.is_file() or not a.cctest.is_file():
    parser.error('selected Node and cctest binaries are required')
sys.path.insert(0, str(a.sdk_source / 'src'))
from emberbsd_sdk.process import ContextLocks, sanitized_environment

env = sanitized_environment()
env['PATH'] = str(a.host_prefix / 'bin')
tests = (
    'test/es-module/test-esm-dynamic-import.js',
    'test/es-module/test-esm-import-meta.mjs',
    'test/parallel/test-worker-esmodule.js',
    'test/parallel/test-worker-process-exit-async-module.js',
    'test/parallel/test-worker-cleanexit-with-moduleload.js',
    'test/parallel/test-worker-terminate-nested.js',
)
with ContextLocks([str(a.host_prefix), str(a.work)], str(a.lock_root), shared=True):
    subprocess.run([str(a.cctest), '--gtest_fail_if_no_test_selected',
                    '--gtest_filter=EnvironmentTest.EmbedderPreload:EnvironmentTest.LoadEnvironmentWithESModule:EnvironmentTest.NoRegisterESMLoaderPreservesEmbedderCallbacks:EnvironmentTest.EmbedderBuiltinCodeCache'],
                   cwd=a.source, env=env, timeout=90, check=True)
    for name in tests:
        subprocess.run([str(a.node), str(a.source / name)], cwd=a.source, env=env, timeout=90, check=True)
        print(name, 'PASS', flush=True)
    stress = Path(__file__).with_name('node-embedder-isolates.cjs')
    subprocess.run([str(a.node), '--expose-gc', str(stress)], cwd=a.source, env=env, timeout=120, check=True)
