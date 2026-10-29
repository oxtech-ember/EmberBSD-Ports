#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise actual generated pkgsrc shell wrappers with a selected target."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

if len(sys.argv) != 5:
    raise SystemExit('usage: shell-wrapper-link-phase.py CC CXX BUILDLINK_LIB HOST_PREFIX')
cc, cxx, libdir, prefix = map(Path, sys.argv[1:])
for path in (cc, cxx, libdir, prefix):
    if not path.is_absolute() or not path.exists():
        raise SystemExit('all selected paths must exist and be absolute')
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    env = {k: v for k, v in os.environ.items() if not k.startswith(('LD_', 'DYLD_'))}
    env['PATH'] = str(prefix / 'bin') + ':' + str(prefix / 'gnu/bin')
    log = root / 'wrapper.log'
    env['WRAPPER_LOG'] = str(log)
    for tool, suffix in ((cc, 'c'), (cxx, 'cc')):
        source = root / ('probe.' + suffix)
        source.write_text('int main(void) { return 0; }\n')
        for mode in ('-c', '-E', '-S', '-fsyntax-only', '-M', '-MM'):
            log.unlink(missing_ok=True)
            result = subprocess.run([str(tool), '-Werror=unused-command-line-argument', mode, str(source)], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode:
                raise ValueError(f'{tool.name} {mode} failed: {result.stderr}')
            route = log.read_text()
            actual = next(line for line in route.splitlines() if line.startswith('<.> '))
            if '-L' + str(libdir) in actual:
                raise ValueError('framework library path leaked into ' + mode)
        log.unlink(missing_ok=True)
        result = subprocess.run([str(tool), '-Werror=unused-command-line-argument', '-c', '-L' + str(libdir), str(source)], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if not result.returncode or '-L' + str(libdir) not in result.stderr:
            raise ValueError('explicit caller linker argument was hidden')
        for flag in ('-MD', '-MMD'):
            log.unlink(missing_ok=True)
            output = root / (suffix + flag[1:])
            result = subprocess.run([str(tool), flag, str(source), '-Wl,--no-as-needed', '-ldrm', '-o', str(output)], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode:
                raise ValueError(f'{tool.name} {flag} link failed: {result.stderr}')
            actual = next(line for line in log.read_text().splitlines() if line.startswith('<.> '))
            if '-L' + str(libdir) not in actual:
                raise ValueError('link lost framework library path')
print('PASS: CC/CXX nonlink phases, explicit args and -MD/-MMD links')
