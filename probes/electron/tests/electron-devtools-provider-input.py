#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Provider fingerprint drives Node and TypeScript outputs without touching C++."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(sys.argv[1]) / 'src'))
from emberbsd_sdk import jsonio
owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
ninja = sys.argv[2]
with tempfile.TemporaryDirectory() as temporary:
    work = Path(temporary); env = {'EMBERBSD_DEVTOOLS_PROVIDER_SHA256': 'a' * 64}
    build.write_devtools_identity(work, {'jsonio': jsonio}, env)
    fingerprint = work / 'devtools-provider.json'
    (work / 'build.ninja').write_text('rule copy\n  command = /bin/cp $in $out\n'
        'build node.out: copy devtools-provider.json\n'
        'build ts.out: copy devtools-provider.json\n'
        'build all: phony node.out ts.out\n')
    cpp = work / 'untouched.o'; cpp.write_text('compatible object')
    def run():
        subprocess.run([ninja, '-C', str(work), 'all'], check=True, capture_output=True)
    run()
    node = work / 'node.out'; ts = work / 'ts.out'
    before = (fingerprint.stat().st_mtime_ns, node.stat().st_mtime_ns, ts.stat().st_mtime_ns)
    cpp_before = (cpp.stat().st_ino, cpp.stat().st_mtime_ns)
    build.write_devtools_identity(work, {'jsonio': jsonio}, env); run()
    assert before == (fingerprint.stat().st_mtime_ns, node.stat().st_mtime_ns, ts.stat().st_mtime_ns)
    env['EMBERBSD_DEVTOOLS_PROVIDER_SHA256'] = 'b' * 64
    build.write_devtools_identity(work, {'jsonio': jsonio}, env); run()
    assert 'b' * 64 in node.read_text() and 'b' * 64 in ts.read_text()
    assert (cpp.stat().st_ino, cpp.stat().st_mtime_ns) == cpp_before
print('PASS: provider changes rebuild Node/TS outputs; no-op and C++ stay unchanged')
