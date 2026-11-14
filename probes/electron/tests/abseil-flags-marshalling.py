#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Apply the real unbundle fix to prepared Chromium sources with zero fuzz."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True, help='prepared pre-patch Chromium src')
p.add_argument('--patch-tool', type=Path, required=True)
p.add_argument('--sysroot', type=Path, required=True)
a = p.parse_args()
owner = Path(__file__).resolve().parents[1]
source = a.source / 'build/linux/unbundle/absl_flags.gn'
patch = owner / 'patches/gn-absl-flags-marshalling.patch'
with tempfile.TemporaryDirectory() as temp:
    dest = Path(temp) / 'build/linux/unbundle/absl_flags.gn'
    dest.parent.mkdir(parents=True)
    dest.write_bytes(source.read_bytes())
    subprocess.run([str(a.patch_tool), '-p1', '--fuzz=0', '-i', str(patch)],
                   cwd=temp, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = dest.read_text()
    assert 'pkg_config("system_absl_flags_marshalling")' in data
    assert 'packages = [ "absl_flags_marshalling" ]' in data
    assert 'headers = [ "marshalling.h" ]' in data
    assert re.search(r'source_set\("marshalling"\)\s*\{[^}]*deps = \[ ":marshalling_shim" \][^}]*public_configs = \[ ":system_absl_flags_marshalling" \]', data, re.S)
    full = (a.source / 'third_party/abseil-cpp/BUILD.gn').read_text()
    assert '//third_party/abseil-cpp/absl/flags:marshalling' in full
    assert (a.sysroot / 'usr/pkg/include/absl/flags/marshalling.h').is_file()
    assert (a.sysroot / 'usr/pkg/lib/pkgconfig/absl_flags_marshalling.pc').is_file()
print('PASS: Abseil full dependency has the installed marshalling shim')
