#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Installed helper interpreter contract.
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 4:
    sys.exit('Use CLANG_STAGE LLD_STAGE LIT_STAGE HOST_PYTHON')
clang, lld, lit = map(Path, args[:3])
python = args[3]
cross = Path(__file__).resolve().parents[1] / 'cross'
sys.path.insert(0, str(cross))
spec = importlib.util.spec_from_file_location('preparer', cross / 'prepare-llvm-python315.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
for stage, names in [(clang, helper.SCRIPTS), (lit, ['bin/lit', 'bin/llvm-lit'])]:
    for name in names:
        assert (stage / name).read_bytes().splitlines()[0] == b'#!/usr/pkg/bin/python3.15', name
for stage in (clang, lld, lit):
    assert not re.search(r'^@pkgdep (python314|py314-)', (stage / '+CONTENTS').read_text(), re.M)
assert re.search(r'^@pkgdep python315>=3\.15\.0$', (clang / '+CONTENTS').read_text(), re.M)
assert '@pkgcfl py[0-9]*-llvm-lit-[0-9]*\n' in (lit / '+CONTENTS').read_text()
modules = [p for name in ('lib/libscanbuild', 'lib/libear', 'share/scan-view', 'share/clang') for p in (clang / name).rglob('*.py')]
subprocess.run([python, '-B', '-c', 'import pathlib,sys; [compile(pathlib.Path(p).read_bytes(), p, "exec") for p in sys.argv[1:]]', *map(str, set(modules + [clang / p for p in helper.SCRIPTS]))], check=True)
print(f'PASS: 13 Clang entry points, two lit launchers, {len(modules)} installed modules and runtime metadata')
