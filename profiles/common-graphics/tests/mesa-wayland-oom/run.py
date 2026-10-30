#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test allocation failures against the selected Mesa Wayland implementation."""
import json
import os
from pathlib import Path
import re
import resource
import shlex
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mesa_test_source import selected, patch, extract

if len(sys.argv) != 3:
    raise SystemExit('Usage: run.py MESA_ARCHIVE NEW_OUTPUT')
archive, distname, info, _ = selected(sys.argv[1])
work = Path(sys.argv[2])
if not work.is_absolute() or work.exists():
    raise SystemExit('Use a new absolute output directory')
cc, patch_tool = os.environ.get('CC'), os.environ.get('PATCH')
if not cc or not patch_tool or not Path(cc).is_absolute() or not Path(patch_tool).is_absolute():
    raise SystemExit('Set CC and PATCH to the selected absolute native tools')
source_path = 'src/egl/drivers/dri2/platform_wayland.c'
delta = patch(info, 'patch-src_egl_drivers_dri2_platform__wayland.c')
source = extract(archive, distname, source_path)
work.mkdir()
for variant in ('baseline', 'patched'):
    target = work / variant / source_path
    target.parent.mkdir(parents=True)
    target.write_bytes(source)

def run(command, log, expected=0, cwd=None):
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1')
    def no_core():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    result = subprocess.run([str(x) for x in command], cwd=cwd, env=env, text=True,
                            capture_output=True, preexec_fn=no_core)
    log.write_text(shlex.join([str(x) for x in command]) + '\n' + result.stdout + result.stderr +
                   '\nexit=' + str(result.returncode) + '\n')
    if result.returncode != expected:
        raise RuntimeError('Unexpected result: ' + str(log))
    return result.stdout + result.stderr

run([patch_tool, '-p0', '-i', delta], work / 'patch.log', cwd=work / 'patched')
methods = ('wait_for_free_buffer', 'get_back_bo', 'update_buffers', 'update_buffers_if_needed',
           'image_get_buffers', 'dri2_wl_swap_buffers_with_damage')
commands = []
for variant in ('baseline', 'patched'):
    directory = work / variant
    text = (directory / source_path).read_text()
    bodies = []
    for name in methods:
        match = re.search(r'^static (?:int|void|EGLBoolean)\n' + re.escape(name) + r'\(.*?^}', text, re.M | re.S)
        if not match:
            raise ValueError('Missing ' + name)
        bodies.append(match.group())
    (directory / 'wayland-methods.inc').write_text('\n\n'.join(bodies) + '\n')
    shutil.copyfile(Path(__file__).with_name('contract.c'), directory / 'contract.c')
    for mode in ('normal', 'sanitized'):
        flags = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer'] if mode == 'sanitized' else []
        command = [cc, '-std=gnu11', '-Wall', '-Wextra', *flags, str(directory / 'contract.c'), '-o', str(directory / mode)]
        if mode == 'normal':
            commands.append(dict(directory=str(directory), arguments=command, file=str(directory / 'contract.c')))
        run(command, work / (variant + '-' + mode + '-build.log'))
        output = run([directory / mode], work / (variant + '-' + mode + '.log'), 1 if variant == 'baseline' else 0)
        if variant == 'baseline' and 'allocation failure leaves a usable back alias' not in output:
            raise AssertionError('Wrong baseline failure')
(work / 'compile_commands.json').write_text(json.dumps(commands, indent=2) + '\n')
print('PASS: Wayland allocation failure, retry and recovery; normal/ASan/UBSan')
