#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check the real common WASM inputs and target runtime path in the loader."""
import argparse
import base64
from pathlib import Path
import re
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--host-prefix', type=Path, required=True)
a = p.parse_args()
script = Path(__file__).resolve().parents[1] / 'files/generate-wasm.py'
wasm = a.host_prefix / 'share/llhttp-wasi'
with tempfile.TemporaryDirectory(prefix='undici-generator-') as temp:
    output = Path(temp)
    loader = output / 'loader.js'
    def run(runtime):
        return subprocess.run([sys.executable, '-B', '-I', '-S', str(script),
            '--wasm-dir', str(wasm), '--output-dir', str(output), '--loader', str(loader),
            '--install-dir', runtime], text=True, capture_output=True)
    assert run('relative').returncode != 0
    r = run('/usr/pkg/lib/node_modules/undici'); assert r.returncode == 0, r.stderr
    text = loader.read_text()
    assert '/usr/pkg/lib/node_modules/undici/loader.js' in text
    assert str(a.host_prefix) not in text and str(output) not in text
    for js, binary in (('llhttp-wasm.js', 'llhttp.wasm'), ('llhttp_simd-wasm.js', 'llhttp_simd.wasm')):
        encoded = re.search(r"const wasmBase64 = '([^']+)'", (output / js).read_text()).group(1)
        assert base64.b64decode(encoded, validate=True) == (wasm / binary).read_bytes()
print('Undici shared WASM and target runtime loader path PASS')
