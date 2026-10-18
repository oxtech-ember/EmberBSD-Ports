#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual selector link lifetime checks.
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 2:
    sys.exit('Use SELECTOR NEW_OUTPUT')
helper, work = Path(args[0]).resolve(), Path(args[1]).absolute()
work.mkdir()
full = ['lib/runtime.so', 'lib/runtime-alias.so', 'lib/sdk.a', 'lib/sdk-alias.a']
runtime, sdk_files = full[:2], full[2:]
cases = [('normal-runtime', 'runtime', 'runtime.so', 'runtime.so', True), ('sdk-to-runtime', 'devel', 'runtime.so', 'runtime.so', True),
    ('runtime-to-sdk', 'runtime', 'sdk.a', 'runtime.so', False), ('runtime-via-sdk', 'runtime', 'sdk-alias.a', 'runtime.so', False),
    ('parent-link', 'runtime', '../lib/runtime.so', 'runtime.so', True), ('file-slash', 'runtime', 'runtime.so/', 'runtime.so', False),
    ('absolute-link', 'runtime', '/lib/runtime.so', 'runtime.so', False), ('escaping-link', 'runtime', '../../outside', 'runtime.so', False),
    ('missing-link', 'runtime', 'missing.so', 'runtime.so', False), ('cyclic-link', 'runtime', 'runtime-alias.so', 'runtime.so', False),
    ('sdk-absolute-link', 'devel', 'runtime.so', '/lib/runtime.so', False)]


def snapshot(stage):
    return {str(p.relative_to(stage)): ['link', os.readlink(p)] if p.is_symlink() else ['file', p.read_bytes()] for p in stage.rglob('*') if p.is_symlink() or p.is_file()}


for label, part, runtime_link, sdk_link, accepted in cases:
    directory = work / label
    stage = directory / 'stage'
    (stage / 'lib').mkdir(parents=True)
    (stage / 'lib/runtime.so').write_text('runtime fixture')
    (stage / 'lib/sdk.a').write_text('SDK fixture')
    (stage / 'lib/runtime-alias.so').symlink_to(runtime_link)
    (stage / 'lib/sdk-alias.a').symlink_to(sdk_link)
    wanted = runtime if part == 'runtime' else sdk_files
    for i, entries in enumerate((full, runtime, sdk_files, wanted)):
        (directory / str(i)).write_text('\n'.join(entries) + '\n')
    before = snapshot(stage)
    result = subprocess.run([sys.executable, '-B', str(helper), '--sdk-source', sdk, part, str(stage), *[str(directory / str(i)) for i in range(4)]], capture_output=True, text=True)
    (directory / 'result.log').write_text(result.stdout + result.stderr)
    assert (result.returncode == 0) == accepted, label + ': ' + result.stdout + result.stderr
    assert snapshot(stage) == ({k: v for k, v in before.items() if k in wanted} if accepted else before)
print('PASS: eleven text/symlink fixtures; no target execution')
