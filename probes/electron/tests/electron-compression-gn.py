#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the actual libphonenumber Brotli action tracks selected host inputs."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'gn', 'ninja', 'python', 'patch', 'brotli'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
owner = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='compression-gn-') as tmp:
    root = Path(tmp)
    files = ('build/linux/unbundle/brotli.gn', 'tools/grit/grit_rule.gni',
             'third_party/libphonenumber/BUILD.gn')
    for name in files:
        dst = root / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(a.source / name, dst)
    (root / 'build/config').mkdir(parents=True, exist_ok=True)
    subprocess.run([str(a.patch), '-p1', '-F0', '-i', str(owner / 'patches/gn-common-brotli-native-tool.patch')], cwd=root, check=True)
    build = root / 'third_party/libphonenumber/BUILD.gn'
    source = build.read_text()
    start = source.index('_brotli_target =')
    end = source.index('\n# Library used by clients', start)
    build.write_text('import("//build/config/emberbsd_brotli.gni")\n' + source[start:end])
    metadata = root / 'third_party/libphonenumber/src/cpp/src/phonenumbers/lite_metadata.cc'
    metadata.parent.mkdir(parents=True)
    metadata.write_text('fixture\n')
    script = root / 'third_party/libphonenumber/gen_compressed_metadata.py'
    script.write_text('import pathlib,sys\na=sys.argv\npathlib.Path(a[a.index("--output")+1]).write_text(a[a.index("--brotli")+1])\n')
    selected = root / 'selected-brotli'
    shutil.copy2(a.brotli, selected)
    runtime = root / 'runtime-input'
    runtime.write_text('first')
    (root / '.gn').write_text('buildconfig = "//config.gn"\nscript_executable = "' + str(a.python.resolve()) + '"\n')
    (root / 'config.gn').write_text('set_default_toolchain("//:test")\nhost_toolchain="//:test"\nhost_os="mac"\n')
    (root / 'BUILD.gn').write_text('toolchain("test") { tool("stamp") { command = "touch {{output}}" } tool("action") {} tool("copy") { command = "cp {{source}} {{output}}" } }\ngroup("all") { deps = [ "//third_party/libphonenumber:gen_lite_metadata_compressed", "//grit:selected" ] }\n')
    grit_source = (root / 'tools/grit/grit_rule.gni').read_text()
    grit_start = grit_source.index('    # Add brotli executable if using brotli.')
    grit_end = grit_source.index('    _resource_ids =', grit_start)
    grit_block = grit_source[grit_start:grit_end]
    grit = root / 'grit/BUILD.gn'
    grit.parent.mkdir()
    grit.write_text('import("//build/config/emberbsd_brotli.gni")\n'
                    'template("grit_fixture") { action(target_name) {\n'
                    'script = "//third_party/libphonenumber/gen_compressed_metadata.py"\n'
                    'inputs = []\noutputs = [ "$target_gen_dir/grit.out" ]\n'
                    'args = [ "--output", rebase_path(outputs[0], root_build_dir) ]\n' +
                    grit_block + ' } }\ngrit_fixture("selected") { use_brotli = true }\n')
    b = root / 'third_party/brotli/BUILD.gn'
    b.parent.mkdir(parents=True)
    b.write_text('copy("brotli") { sources=["//selected-brotli"] outputs=["$root_out_dir/brotli"] }\n')
    out = root / 'out'
    args = 'emberbsd_brotli_native_tool="' + str(selected) + '" emberbsd_brotli_native_inputs=["' + str(runtime) + '"]'
    subprocess.run([str(a.gn), 'gen', str(out), '--args=' + args], cwd=root, check=True)
    desc = subprocess.check_output([str(a.gn), 'desc', str(out), '//third_party/libphonenumber:gen_lite_metadata_compressed', '--format=json'], text=True, stderr=subprocess.STDOUT, cwd=root)
    assert str(selected) in desc and str(runtime) in desc
    output = out / 'gen/third_party/libphonenumber/lite_metadata_compressed.cc'
    grit_output = out / 'gen/grit/grit.out'
    cmd = [str(a.ninja), '-C', str(out), str(output.relative_to(out)), str(grit_output.relative_to(out))]
    subprocess.run(cmd, check=True, capture_output=True)
    assert (out / output.read_text()).resolve() == selected.resolve()
    assert (out / grit_output.read_text()).resolve() == selected.resolve()
    before = (output.stat().st_mtime_ns, grit_output.stat().st_mtime_ns)
    subprocess.run(cmd, check=True, capture_output=True)
    assert (output.stat().st_mtime_ns, grit_output.stat().st_mtime_ns) == before
    for changed in (runtime, selected):
        time.sleep(1.1)
        changed.touch()
        subprocess.run(cmd, check=True, capture_output=True)
        after = (output.stat().st_mtime_ns, grit_output.stat().st_mtime_ns)
        assert all(new > old for new, old in zip(after, before)), str(changed) + ' did not invalidate the action'
        before = after
print('PASS: actual GN action uses selected Brotli and rebuilds only when its inputs change')
