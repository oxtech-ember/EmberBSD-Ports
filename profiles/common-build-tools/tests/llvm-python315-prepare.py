#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real package tools; labelled script fixtures.
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 3:
    sys.exit('Use HOST_PKG_CREATE CMAKE NEW_WORK')
create, cmake, directory = args
work = Path(directory).absolute()
work.mkdir()
cross = Path(__file__).resolve().parents[1] / 'cross'
sys.path.insert(0, str(cross))
spec = importlib.util.spec_from_file_location('preparer', cross / 'prepare-llvm-python315.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
source = work / 'source'
source.mkdir()
archives = {}
for kind in ('clang', 'lld', 'lit'):
    stage = work / kind
    stage.mkdir()
    names = list(helper.SCRIPTS) if kind == 'clang' else ['bin/lit', 'bin/llvm-lit'] if kind == 'lit' else ['share/lld/fixture']
    for name in names:
        output = stage / name
        output.parent.mkdir(parents=True, exist_ok=True)
        if kind == 'clang':
            upstream = source / helper.SCRIPTS[name]
            upstream.parent.mkdir(parents=True, exist_ok=True)
            upstream.write_text('#!/usr/bin/env python3\n# Labelled fixture, not an upstream tool.\nprint("fixture")\n')
            output.write_text('#!/usr/pkg/bin/python3.14\n' + '\n'.join(upstream.read_text().splitlines()[1:]) + '\n')
        elif kind == 'lit':
            output.write_text('#!/usr/pkg/bin/python3.15\nprint("fixture")\n')
        else:
            output.write_text('labelled fixture\n')
    name = 'py315-llvm-lit-23.1.4' if kind == 'lit' else kind + '-23.1.4'
    dependency = '@pkgdep py314-llvm-lit>=23.1.4\n' if kind != 'lit' else '@pkgdep python315>=3.15.0\n'
    plist = work / (kind + '.plist')
    plist.write_text('@cwd /usr/pkg\n@name ' + name + '\n' + dependency + '\n'.join(names) + '\n')
    for control, text in {'comment': 'Labelled fixture', 'desc': 'No compiler payload or target execution.', 'build': 'OPSYS=NetBSD\nMACHINE_ARCH=aarch64\n'}.items():
        (stage / control).write_text(text)
    archive = work / (name + '.tgz')
    subprocess.run([create, '-p', str(stage), '-I', '/usr/pkg', '-f', str(plist), '-c', str(stage / 'comment'), '-d', str(stage / 'desc'), '-B', str(stage / 'build'), str(archive)], check=True, capture_output=True)
    archives[kind] = str(archive)
command = [sys.executable, '-B', str(cross / 'prepare-llvm-python315.py'), '--sdk-source', sdk]
for name, value in dict(archives, **{'clang-source': str(source), 'python': sys.executable, 'cmake': cmake, 'readelf': '/usr/bin/true', 'pkg-create': create}).items():
    command += ['--' + name, value]
# No ELF payload occurs here. The readelf compatibility input is not executed.
result = subprocess.run(command + [str(work / 'accepted')], capture_output=True, text=True)
(work / 'accepted.log').write_text(result.stdout + result.stderr)
assert result.returncode == 0, result.stdout + result.stderr
receipt = json.loads((work / 'accepted/receipt.json').read_text())
assert len(receipt['packages']) == 3
subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('llvm-python315-payload.py')), '--sdk-source', sdk, str(work / 'accepted/clang'), str(work / 'accepted/lld'), str(work / 'accepted/lit'), sys.executable], check=True)
original = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('llvm-python315-payload.py')), '--sdk-source', sdk, str(work / 'clang'), str(work / 'lld'), str(work / 'lit'), sys.executable], capture_output=True, text=True)
assert original.returncode, 'Old interpreter fixture was accepted'
next(iter(source.rglob('analyze-build'))).write_text('unrelated source\n')
rejected = subprocess.run(command + [str(work / 'rejected')], capture_output=True, text=True)
(work / 'rejected.log').write_text(rejected.stdout + rejected.stderr)
assert rejected.returncode and 'Unexpected interpreter or upstream script' in rejected.stderr
assert not list((work / 'rejected').glob('*.tgz'))
print('PASS: bounded preparation and installed-script checks with real pkgtools; changed upstream body rejected')
print('SCOPE: labelled script-only archives; no ELF RPATH operation, compiler build or target acceptance')
