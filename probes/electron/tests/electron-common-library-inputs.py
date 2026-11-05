#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Selected library files become Ninja link inputs; unrelated files do not."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
gn, ninja = sys.argv[1:3]
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary).resolve(); (root / 'lib').mkdir(); (root / 'pkgdb/pkg').mkdir(parents=True)
    library = root / 'lib/libexample.so.1'; library.write_text('v1')
    (root / 'lib/libexample.so').symlink_to(library.name)
    package = root / 'pkgdb/pkg'; (package / '+CONTENTS').write_text('lib/libexample.so\nlib/libexample.so.1\n')
    selected = build.selected_owned_library(root, 'libexample.so', [package]); assert selected == str(library)
    (package / '+CONTENTS').write_text('lib/libexample.so\n')
    try:
        build.selected_owned_library(root, 'libexample.so', [package]); raise AssertionError('unowned payload accepted')
    except ValueError:
        pass
    (root / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n')
    (root / 'BUILDCONFIG.gn').write_text('set_default_toolchain("//:host")\n')
    (root / 'BUILD.gn').write_text('toolchain("host") {\n  tool("link") {\n'
        '    command = "/bin/cp {{libs}} {{output}}"\n'
        '    outputs = [ "{{root_out_dir}}/{{target_output_name}}" ]\n'
        '    default_output_extension = ""\n  }\n}\n'
        'executable("app") {\n  libs = [ "' + selected + '" ]\n}\n')
    out = root / 'out'
    subprocess.run([gn, 'gen', str(out), '--root=' + str(root)], check=True, capture_output=True)
    def run(): return subprocess.run([ninja, '-C', str(out), 'app'], check=True, capture_output=True, text=True)
    run(); output = out / 'app'; assert output.read_text() == 'v1'
    before = output.stat().st_mtime_ns
    (root / 'unrelated').write_text('x'); run(); assert output.stat().st_mtime_ns == before
    library.write_text('v2'); run(); assert output.read_text() == 'v2'
print('PASS: selected pkgdb-owned library relinks; unrelated file does not')
