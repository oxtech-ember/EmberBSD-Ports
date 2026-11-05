#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the flatbuffer action using actual GN and selected host flatc."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'gn', 'flatc', 'python', 'patch', 'ninja'):
    p.add_argument('--' + name, required=True, type=Path)
a = p.parse_args()
source = a.source.resolve(strict=True)
owner = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='flatc-gn-') as temp:
    root = Path(temp)
    for name in ('build/config/sanitizers', 'third_party/flatbuffers', 'schema'):
        (root / name).mkdir(parents=True)
    (root / '.gn').write_text('buildconfig = "//config.gn"\nscript_executable = "' + str(a.python.resolve()) + '"\n')
    (root / 'config.gn').write_text('set_default_toolchain("//:test")\nhost_toolchain = "//:test"\nhost_os = "mac"\nbuild_with_chromium = false\nhost_toolchain_is_msan = false\n')
    (root / 'build/config/sanitizers/sanitizers.gni').write_text('')
    shutil.copyfile(source / 'build/compiled_action.gni', root / 'build/compiled_action.gni')
    shutil.copyfile(source / 'build/gn_run_binary.py', root / 'build/gn_run_binary.py')
    shutil.copyfile(source / 'third_party/flatbuffers/flatbuffer.gni', root / 'third_party/flatbuffers/flatbuffer.gni')
    subprocess.run([str(a.patch.resolve(strict=True)), '-p1', '-F0', '-i', str(owner / 'patches/gn-shared-flatc.patch')], cwd=root, check=True)
    (root / 'schema/sample.fbs').write_text('namespace fixture; table Example { value:int; } root_type Example;\n')
    (root / 'third_party/flatbuffers/BUILD.gn').write_text('group("flatbuffers") {}\ncopy("flatc") { sources = [ "//schema/sample.fbs" ] outputs = [ "$root_out_dir/flatc" ] }\n')
    (root / 'BUILD.gn').write_text('''import("//third_party/flatbuffers/flatbuffer.gni")
toolchain("test") {
  tool("stamp") { command = "touch {{output}}" }
  tool("action") {}
  tool("copy") { command = "cp {{source}} {{output}}" }
}
flatbuffer("sample") { sources = [ "//schema/sample.fbs" ] }
''')
    out = root / 'out'
    flatc = str(a.flatc.resolve(strict=True))
    runtime = root / 'runtime.dylib'
    runtime.write_bytes(b'fixture')
    args = 'emberbsd_flatc="' + flatc + '" emberbsd_flatc_inputs=["' + flatc + '","' + str(runtime) + '"]'
    subprocess.run([str(a.gn), 'gen', str(out), '--args=' + args], cwd=root, check=True)
    desc = subprocess.run([str(a.gn), 'desc', str(out), '//:sample_gen', '--format=json'], cwd=root, check=True, text=True, capture_output=True).stdout
    if flatc not in desc or str(runtime) not in desc or 'third_party/flatbuffers:flatc' in desc:
        raise SystemExit('selected action did not bind explicit flatc')
    subprocess.run([str(a.ninja.resolve(strict=True)), '-C', str(out), 'gen/schema/sample_generated.h'], check=True)
    generated = out / 'gen/schema/sample_generated.h'
    if not generated.is_file():
        raise SystemExit('expected generated header is absent')
    reference = root / 'reference'
    reference.mkdir()
    subprocess.run([flatc, '-c', '--keep-prefix', '-o', str(reference), '-I', str(root), str(root / 'schema/sample.fbs')], check=True)
    if generated.read_bytes() != (reference / 'sample_generated.h').read_bytes():
        raise SystemExit('generated output differs from direct upstream flatc')
    fallback = root / 'fallback'
    subprocess.run([str(a.gn), 'gen', str(fallback)], cwd=root, check=True)
    previous = subprocess.run([str(a.gn), 'desc', str(fallback), '//:sample_gen', '--format=json'], cwd=root, check=True, text=True, capture_output=True).stdout
    if 'third_party/flatbuffers:flatc' not in previous:
        raise SystemExit('unset selection did not retain bundled target')
    bad = subprocess.run([str(a.gn), 'gen', str(root / 'invalid'), '--args=emberbsd_flatc="' + flatc + '"'], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if bad.returncode == 0:
        raise SystemExit('missing runtime inputs accepted')
print('PASS: selected flatc GN action uses common executable and generates expected header')
