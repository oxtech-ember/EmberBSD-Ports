#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the installed shared ABI using pkg-config on Darwin."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
for option in ('prefix', 'stage-root', 'cc', 'pkg-config', 'install-name-tool'):
    parser.add_argument('--' + option, type=Path, required=True)
parser.add_argument('--flag', action='append', default=[])
a = parser.parse_args()
stage = a.stage_root / str(a.prefix).lstrip('/')
env = os.environ.copy()
env['PKG_CONFIG_PATH'] = str(stage / 'lib/pkgconfig')
env['PKG_CONFIG_SYSROOT_DIR'] = str(a.stage_root)
flags = shlex.split(subprocess.check_output(
    [str(a.pkg_config), '--cflags', '--libs', 'simdjson'], env=env, text=True))
assert '-DSIMDJSON_THREADS_ENABLED=1' in flags
with tempfile.TemporaryDirectory(prefix='simdjson-abi-') as d:
    root = Path(d)
    library = root / 'libsimdjson.34.dylib'
    shutil.copyfile(stage / 'lib/libsimdjson.34.0.0.dylib', library)
    (root / 'libsimdjson.dylib').symlink_to(library.name)
    subprocess.run([str(a.install_name_tool), '-id', str(library), str(library)], check=True)
    flags = ['-L' + str(root) if flag.startswith('-L') else flag for flag in flags]
    results = []
    for opt in ('0', '2'):
        executable = root / ('stream-' + opt)
        subprocess.run([str(a.cc), *a.flag, '-std=c++17', '-O' + opt,
                        str(Path(__file__).with_name('stream.cpp')), *flags,
                        '-o', str(executable)], check=True)
        results.append(subprocess.check_output([str(executable)], text=True).strip())
    assert results[0] == results[1], results
    print('pkg-config shared ABI -O0/-O2:', results[0])
