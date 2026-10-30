#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test the selected Mesa V3D cache mutex lifecycle and causal mutations."""
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
archive, distname, info, digest = selected(sys.argv[1])
work = Path(sys.argv[2])
if not work.is_absolute() or work.exists():
    raise SystemExit('Use a new absolute output directory')
cc, patch_tool = os.environ.get('CC'), os.environ.get('PATCH')
if not cc or not patch_tool or not Path(cc).is_absolute() or not Path(patch_tool).is_absolute():
    raise SystemExit('Set CC and PATCH to selected absolute native tools')
delta = patch(info, 'patch-src_gallium_drivers_v3d_v3d__screen.c')
paths = ('src/gallium/drivers/v3d/v3d_screen.c', 'src/gallium/drivers/v3d/v3d_bufmgr.c', 'src/util/list.h')
work.mkdir()
for path in paths:
    content = extract(archive, distname, path)
    for variant in ('baseline', 'patched'):
        target = work / variant / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

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
fixed = (work / 'patched' / paths[0]).read_text()
mutants = {
    'missing-cache-init': ('if (mtx_init(&screen->bo_cache.lock, mtx_plain) != thrd_success)', 'if (0)'),
    'ignored-init-failure': ('if (mtx_init(&screen->bo_cache.lock, mtx_plain) != thrd_success)', 'if (mtx_init(&screen->bo_cache.lock, mtx_plain) == -99)'),
    'missing-normal-destroy': ('        mtx_destroy(&screen->bo_cache.lock);\n', ''),
    'missing-unwind': ('fail_handles_mutex:\n        mtx_destroy(&screen->bo_handles_mutex);', 'fail_handles_mutex:\n'),
    'early-destroy': ('        v3d_bufmgr_destroy(pscreen);\n        mtx_destroy(&screen->bo_handles_mutex);\n        mtx_destroy(&screen->bo_cache.lock);', '        mtx_destroy(&screen->bo_cache.lock);\n        mtx_destroy(&screen->bo_handles_mutex);\n        v3d_bufmgr_destroy(pscreen);'),
}
for name, (old, new) in mutants.items():
    changed = fixed.replace(old, new, 1)
    if changed == fixed:
        raise ValueError('Ineffective mutant ' + name)
    target = work / name / paths[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(changed)
commands = []
for variant in ('baseline', 'patched', *mutants):
    directory = work / variant
    screen = (directory / paths[0]).read_text()
    buffer = (work / 'baseline' / paths[1]).read_text()
    patterns = ((buffer, r'^static void\nv3d_bo_cache_free_all\([^;{]*\)\n\{.*?^}'),
                (buffer, r'^void\nv3d_bufmgr_destroy\(.*?^}'),
                (screen, r'^static void\nv3d_screen_destroy\(.*?^}'),
                (screen, r'^struct pipe_screen \*\nv3d_screen_create\(.*?^}'))
    functions = []
    for text, pattern in patterns:
        match = re.search(pattern, text, re.M | re.S)
        if not match:
            raise ValueError('Missing real V3D function')
        functions.append(match.group())
    (directory / 'lifecycle.inc').write_text('\n\n'.join(functions) + '\n')
    shutil.copyfile(work / 'baseline' / paths[2], directory / 'list.h')
    shutil.copyfile(Path(__file__).with_name('contract.c'), directory / 'contract.c')
    for mode in ('normal', 'sanitized'):
        for simulator in (0, 1):
            flags = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer'] if mode == 'sanitized' else []
            output = directory / (mode + '-' + str(simulator))
            command = [cc, '-std=gnu11', '-Wall', '-Wextra', *flags, '-DUSE_V3D_SIMULATOR=' + str(simulator),
                       *(['-DENABLE_SHADER_CACHE'] if simulator == 0 else []), str(directory / 'contract.c'), '-pthread', '-o', str(output)]
            if mode == 'normal':
                commands.append(dict(directory=str(directory), arguments=command, file=str(directory / 'contract.c')))
            run(command, Path(str(output) + '-build.log'))
            text = run([output], Path(str(output) + '.log'), 0 if variant == 'patched' else 1)
            if variant == 'baseline' and 'screen published without both initialized mutexes' not in text:
                raise AssertionError('Wrong baseline failure')
(work / 'compile_commands.json').write_text(json.dumps(commands, indent=2) + '\n')
(work / 'results.json').write_text(json.dumps(dict(source_sha512=digest, normal_and_asan_ubsan='PASS',
    baseline='rejects uninitialized cache mutex', mutants=list(mutants), simulator_variants=[0, 1], hardware='NOT TESTED'), indent=2) + '\n')
print('PASS: V3D lifecycle, five causal mutants; normal/ASan/UBSan')
