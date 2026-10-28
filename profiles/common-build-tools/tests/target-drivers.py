#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the recipe driver check with selected Clang and alternate profiles."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('shell', 'cc', 'cxx'):
    p.add_argument('--'+name, type=Path, required=True)
p.add_argument('--gnu-triplet', required=True)
p.add_argument('--rust-triple', required=True)
a = p.parse_args()
helper = Path(__file__).resolve().parents[1] / 'verify-target-drivers.sh'
def verify(cc, cxx, expected):
    r = subprocess.run([str(a.shell), str(helper), str(cc), str(cxx), a.gnu_triplet, a.rust_triple],
                       text=True, capture_output=True)
    if (r.returncode == 0) != expected:
        raise AssertionError(r.stderr)
verify(a.cc, a.cxx, True)
with tempfile.TemporaryDirectory(prefix='sdk-driver-test-') as tmp:
    root = Path(tmp)
    def driver(name, target, version, full=None):
        path = root/name
        path.write_text(f'#!{a.shell}\ncase "$1" in -dumpmachine) echo {target};; -dumpversion) echo {version};; -dumpfullversion) ' + (f'echo {full};;' if full else 'exit 2;;') + ' *) exit 2;; esac\n')
        path.chmod(0o755)
        return path
    gcc = driver('gcc', a.gnu_triplet, '16', '16.2.0')
    gxx = driver('gxx', a.gnu_triplet, '16', '16.2.0')
    verify(gcc, gxx, True)
    verify(gcc, driver('wrong-target', 'x86_64-unknown-linux-gnu', '16'), False)
    verify(gcc, driver('wrong-version', a.gnu_triplet, '16', '16.3.0'), False)
    verify(driver('wrong-both', 'x86_64-unknown-linux-gnu', '16'),
           driver('wrong-both-cxx', 'x86_64-unknown-linux-gnu', '16'), False)
print('selected Clang and alternate GCC target/version validation: PASS')
