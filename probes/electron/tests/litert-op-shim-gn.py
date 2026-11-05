#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check the restored shim's source-view GN wiring against upstream files."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True, help='unpatched Chromium source root')
parser.add_argument('--patch-tool', default='patch')
args = parser.parse_args()
patch = Path(__file__).resolve().parents[1] / 'patches/litert-common-op-shim.patch'
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for name in ('third_party/litert/BUILD.gn', 'third_party/tflite/BUILD.gn'):
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.source / name, destination)
    with patch.open('rb') as source:
        subprocess.run([args.patch_tool, '-p1', '-F0', '-s'], cwd=root, stdin=source, check=True)
    litert = (root / 'third_party/litert/BUILD.gn').read_text()
    tflite = (root / 'third_party/tflite/BUILD.gn').read_text()
    assert litert.count('tflite_static_library("tflite_op_shim")') == 1
    for name in ('shape.cc', 'tflite_op_shim.cc', 'tflite_tensor_view.cc'):
        assert litert.count('src/tflite/kernels/shim/' + name) == 1
    assert litert.count('conditional_public_deps += [ ":tflite_op_shim" ]') == 1
    assert 'conditional_public_deps = [ "//third_party/litert:tflite_op_shim" ]' in tflite
    for platform in ('windows', 'default'):
        assert litert.count('/platform/' + platform + '/env_time.cc') == 1
print('PASS: common shim target, public dependencies, and one TSL clock per platform')
