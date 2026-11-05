#!/usr/bin/env python3
"""Actual cppgir lookup regression: target GIR only, including recursive deps."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

if len(sys.argv) != 5:
    raise SystemExit('usage: strict-gir.py CPPGIR IGNORE_DIR TARGET_GIR_DIR HOST_GIR_DIR')
exe, data, target, host = map(lambda x: Path(x).resolve(), sys.argv[1:])
for p in (exe, data / 'cppgir.ignore', data / 'cppgir_unix.ignore', target / 'Gio-2.0.gir', target / 'GLib-2.0.gir', host / 'GLib-2.0.gir', host / 'Gio-2.0.gir'):
    if not p.is_file():
        raise SystemExit(f'missing fixture input: {p}')
env = os.environ.copy()
for k in ('GI_GIR', 'GI_GIR_PATH', 'GI_IGNORE'):
    env.pop(k, None)
env['XDG_DATA_HOME'] = str(host.parent)
with tempfile.TemporaryDirectory(prefix='cppgir-strict-gir-') as tmp:
    root = Path(tmp); empty = root / 'empty'; partial = root / 'partial'; cwd = root / 'cwd'
    for p in (empty, partial, cwd): p.mkdir()
    for p in target.glob('*.gir'):
        if p.name != 'GLib-2.0.gir': shutil.copy2(p, partial / p.name)
    shutil.copy2(host / 'GLib-2.0.gir', cwd / 'GLib-2.0')
    generated = root / 'generated-top-level.gir'; shutil.copy2(target / 'Gio-2.0.gir', generated)
    def run(name, directory, gir, expected, work=None):
        out = root / name; out.mkdir()
        args = [str(exe), '--no-default-gir-path', '--gir-path', str(directory), '--ignore', f'{data}/cppgir.ignore:{data}/cppgir_unix.ignore', '--class', '--class-full', '--expected', '--output', str(out), str(gir)]
        result = subprocess.run(args, env=env, cwd=work, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if (result.returncode == 0) != expected:
            raise SystemExit(f'{name}: unexpected exit {result.returncode}\n{result.stdout[-3000:]}')
        if not expected and 'could not find GIR' not in result.stdout:
            raise SystemExit(f'{name}: failed for an unrelated reason\n{result.stdout[-3000:]}')
        print(f'PASS: {name}')
    run('target-positive', target, target / 'Gio-2.0.gir', True)
    run('generated-top-level', target, generated, True)
    run('missing-target-host-xdg', empty, 'Gio-2.0', False)
    run('missing-dependency-poisoned-cwd', partial, partial / 'Gio-2.0.gir', False, cwd)
