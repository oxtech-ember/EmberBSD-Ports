#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the patched bootstrap loader selection and real host rustc."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('source', 'rustc', 'host-linker', 'host-prefix'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
text = (a.source / 'src/shim_utils/src/shared_helpers.rs').read_text()
start = text.index('pub fn dylib_path_var()')
end = text.index('\n}\n', start) + 2
function = text[start:end]
program = function + '''\nfn main() {
    let want = if cfg!(target_vendor = "apple") { "DYLD_FALLBACK_LIBRARY_PATH" }
               else if cfg!(target_os = "linux") { "LD_LIBRARY_PATH" }
               else { return };
    assert_eq!(dylib_path_var(), want);
}\n'''
env = os.environ.copy()
env.pop('DYLD_LIBRARY_PATH', None)
env.pop('DYLD_INSERT_LIBRARIES', None)
env['DYLD_FALLBACK_LIBRARY_PATH'] = str(a.host_prefix / 'lib')
with tempfile.TemporaryDirectory(prefix='rust-loader-') as tmp:
    source = Path(tmp) / 'probe.rs'
    exe = Path(tmp) / 'probe'
    source.write_text(program)
    subprocess.run([str(a.rustc), '-C', 'linker=' + str(a.host_linker), str(source), '-o', str(exe)], env=env, check=True)
    subprocess.run([str(exe)], env=env, check=True)
    subprocess.run([str(a.rustc), '-vV'], env=env, check=True, stdout=subprocess.DEVNULL)
print('bootstrap loader selection and host rustc: PASS')
