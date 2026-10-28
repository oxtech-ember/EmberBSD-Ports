#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Compile the actual NetBSD link declarations with both unwinder selections."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--rustc', type=Path, required=True)
p.add_argument('--target', choices=('x86_64-unknown-netbsd', 'aarch64-unknown-netbsd'), required=True)
a = p.parse_args()
text = (a.source / 'library/unwind/src/lib.rs').read_text()
pattern = (r'#\[cfg\(all\(target_os = "netbsd", not\(feature = "system-llvm-libunwind"\)\)\)\]\n'
           r'#\[link\(name = "gcc_s"\)\]\nunsafe extern "C" \{\}\n\n'
           r'#\[cfg\(all\(target_os = "netbsd", feature = "system-llvm-libunwind"\)\)\]\n'
           r'#\[link\(name = "unwind"\)\]\nunsafe extern "C" \{\}')
match = re.search(pattern, text)
if not match: raise SystemExit('missing feature-aware NetBSD unwinder declarations')
body = '#![no_std]\n' + match.group() + '''\n#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! { loop {} }
#[unsafe(no_mangle)]
pub extern "C" fn probe() -> i32 { 42 }
'''
with tempfile.TemporaryDirectory(prefix='rust-netbsd-unwind-') as temp:
    root = Path(temp); source = root/'probe.rs'; source.write_text(body)
    for feature, expected, forbidden in ((False, '-lgcc_s', '-lunwind'), (True, '-lunwind', '-lgcc_s')):
        args = [str(a.rustc), '--target', a.target, '--edition', '2024', '--crate-type', 'staticlib',
                '-C', 'panic=abort', '--print', 'native-static-libs', str(source), '-o', str(root/'probe.a')]
        if feature: args[1:1] = ['--cfg', 'feature="system-llvm-libunwind"']
        result = subprocess.run(args, text=True, capture_output=True, env=dict(os.environ), check=True)
        match_line = re.search(r'native-static-libs: ([^\n]+)', result.stderr)
        if not match_line: raise RuntimeError(result.stderr)
        libraries = match_line.group(1).split()
        if expected not in libraries or forbidden in libraries: raise RuntimeError(str(libraries))
print('NetBSD GCC and system LLVM feature selections: PASS')
