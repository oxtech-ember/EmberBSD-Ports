#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check source-owned EmberBSD native-addon ABI values and header rewriting."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--node-source', type=Path, required=True)
parser.add_argument('--python', type=Path, required=True)
parser.add_argument('--electron-header-generator', type=Path, required=True)
a = parser.parse_args()
source = a.node_source.resolve(strict=True)
python = a.python.resolve(strict=True)
helper = source / 'tools/getmoduleversion.py'
header = source / 'src/node_version.h'

def version(*args):
    return subprocess.check_output([str(python), '-B', str(helper), *args], text=True).strip()

standalone = version()
electron = version('--electron')
assert standalone == '1162674177' and electron == '1162674178'
assert standalone != electron
contents = header.read_text()
assert re.search(r'^#define NODE_MODULE_VERSION ' + standalone + r'$', contents, re.M)
assert re.search(r'^#define NODE_EMBER_ELECTRON_MODULE_VERSION ' + electron + r'$', contents, re.M)
assert 'defined(NODE_EMBEDDER_MODULE_VERSION)' in contents
assert subprocess.run([str(python), '-B', str(helper), '--unknown'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
with tempfile.TemporaryDirectory(prefix='node-ember-abi-') as temp:
    generated = Path(temp) / 'node_version.h'
    subprocess.run([str(python), '-B', str(a.electron_header_generator.resolve(strict=True)), str(header), str(generated), electron], check=True)
    result = generated.read_text()
    assert re.search(r'^#define NODE_MODULE_VERSION ' + electron + r'$', result, re.M)
    assert not re.search(r'^#define NODE_MODULE_VERSION ' + standalone + r'$', result, re.M)
print('Node standalone and Electron source ABI header contract: PASS')
