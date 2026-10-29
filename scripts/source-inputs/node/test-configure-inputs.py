#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run the common helper and Node target configure on a writable source copy."""
import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
for option in ('node-source', 'work', 'v8-source', 'inspector-source', 'sdk-source', 'jinja-root',
               'zlib-source', 'v8-cxx-wrapper', 'v8-selected-clang', 'v8-libclang',
               'v8-python-bindings', 'v8-clang-resource'):
    p.add_argument('--' + option, type=Path, required=True)
a = p.parse_args()
node = a.node_source.resolve(strict=True)
work = a.work.resolve(strict=True)
if not node.is_relative_to(work) or node == work:
    p.error('the writable Node source must be inside the selected work directory')
helper = Path(__file__).with_name('configure-inputs.py')
options = []
for key in ('node_source', 'work', 'v8_source', 'inspector_source', 'sdk_source', 'jinja_root',
            'zlib_source', 'v8_cxx_wrapper', 'v8_selected_clang', 'v8_libclang',
            'v8_python_bindings', 'v8_clang_resource'):
    options += ['--' + key.replace('_', '-'), str(getattr(a, key))]

def call(action, opts, extra=(), expected=0):
    cmd = [sys.executable, '-B', str(helper), action, *opts, *extra]
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=600)
    if (result.returncode == 0) != (expected == 0):
        raise RuntimeError(f'{action} exit {result.returncode}: {result.stdout[-1500:]}{result.stderr[-1500:]}')
    return result

# Refuse provider overlap and a symlink that points out of the writable copy.
blocked = options.copy()
blocked[blocked.index('--node-source') + 1] = str(a.v8_source)
call('prepare', blocked, expected=1)
escape = work / 'negative-node'
(escape / 'deps').mkdir(parents=True, exist_ok=False)
(escape / 'deps/v8').symlink_to(a.v8_source, target_is_directory=True)
blocked = options.copy()
blocked[blocked.index('--node-source') + 1] = str(escape)
call('prepare', blocked, expected=1)

sentinel = node / 'deps/v8/ember-obsolete-v8-fixture'
sentinel.write_text('bundled only\n')
call('configure', options, ['--', '--dest-cpu', 'x64', '--dest-os', 'netbsd',
                           '--with-intl=system-icu', '--experimental-enable-pointer-compression',
                           '--openssl-no-asm'])
if sentinel.exists() or (work / 'node-bundled-v8/ember-obsolete-v8-fixture').read_text() != 'bundled only\n':
    raise AssertionError('bundled V8 was not cleanly replaced and preserved')
config = ast.literal_eval((node / 'config.gypi').read_text())['variables']
if config['node_module_version'] != 1162674177 or config['shlib_suffix'] != 'so.1162674177':
    raise AssertionError('Node configure did not preserve standalone ABI and target suffix')
repeat = call('prepare', options)
data = json.loads(repeat.stdout)
if set(data) != {'gyp_args'} or len(data['gyp_args']) != 11:
    raise AssertionError('prepare output is not the expected JSON argv')
print('PASS: overlap and symlink refusal, clean V8, NetBSD configure and repeat JSON')
