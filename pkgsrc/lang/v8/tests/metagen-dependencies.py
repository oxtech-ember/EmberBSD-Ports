#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Verify real metagen dependency tracking with selected host libclang."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'driver', 'compile-commands', 'libclang', 'bindings',
             'resource', 'gmake', 'work'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
source, driver, commands, libclang, bindings, resource, gmake, work = (
    getattr(a, name.replace('-', '_')).resolve(strict=True) for name in
    ('source', 'driver', 'compile-commands', 'libclang', 'bindings',
     'resource', 'gmake', 'work'))
with tempfile.TemporaryDirectory(prefix='v8-metagen-deps-', dir=work) as temp:
    root = Path(temp); copied = root / 'resource'; copied.mkdir()
    shutil.copytree(resource / 'include', copied / 'include', symlinks=True)
    out = root / 'out'; out.mkdir()
    dep = out / 'result.d'; stamp = out / 'result.stamp'; result = out / 'instance-types.h'
    cmd = [sys.executable, '-B', str(source / 'tools/metagen/metagen.py'),
           '--v8-root', str(source), '--driver', str(driver), '--out', str(out),
           '--depfile', str(dep), '--compile-commands', str(commands),
           '--clang-resource-dir', str(copied), '--libclang-so', str(libclang),
           '--libclang-bindings-dir', str(bindings)]
    # Run from the selected compile command's directory, as the build does.
    import json
    record = json.loads(commands.read_text())
    cwd = Path(record[0]['directory']).resolve(strict=True)
    def generate():
        subprocess.run(cmd, cwd=cwd, check=True)
        target, rest = dep.read_text().split(':', 1)
        dep.write_text(os.path.relpath(stamp, cwd).replace(' ', r'\ ') + ':' + rest)
        stamp.write_text('ok\n')
    generate(); original = result.read_bytes()
    target = os.path.relpath(stamp, cwd).replace(' ', r'\ ')
    import shlex
    runner = root / 'rerun.py'
    runner.write_text('import os, subprocess\n'
                      + 'subprocess.run(' + repr(cmd) + ', cwd=' + repr(str(cwd)) + ', check=True)\n'
                      + 'p=' + repr(str(dep)) + '\n'
                      + 's=open(p).read().split(":", 1)[1]\n'
                      + 'open(p,"w").write(' + repr(target + ':') + '+s)\n'
                      + 'open(' + repr(str(stamp)) + ',"w").write("ok\\n")\n')
    makefile = root / 'test.mk'
    makefile.write_text(target + ':\n\t' + shlex.join([sys.executable, '-B', str(runner)]) +
                        '\ninclude ' + str(dep).replace(' ', r'\ ') + '\n')
    check = [str(gmake), '-f', str(makefile), '-q', target.replace(r'\ ', ' ')]
    assert subprocess.run(check, cwd=cwd).returncode == 0
    header = copied / 'include/__stddef_size_t.h'
    assert header.is_file() and os.path.relpath(header, cwd).replace(' ', r'\ ') in dep.read_text()
    header.write_bytes(header.read_bytes() + b'\n/* metagen dependency test */\n')
    assert subprocess.run(check, cwd=cwd).returncode == 1
    subprocess.run([str(gmake), '-f', str(makefile), target.replace(r'\ ', ' ')], cwd=cwd, check=True)
    assert result.read_bytes() == original
    assert subprocess.run(check, cwd=cwd).returncode == 0
print('metagen resource dependency and stable output PASS')
