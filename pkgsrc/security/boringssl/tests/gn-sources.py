#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check the actual common BoringSSL source lists with the selected GN."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--gn', type=Path, required=True)
p.add_argument('--python', type=Path, required=True)
a = p.parse_args()
assert all(x.is_absolute() for x in (a.source, a.gn, a.python))
with tempfile.TemporaryDirectory(prefix='boringssl-gn-') as temp:
    root = Path(temp)
    (root / 'gen').mkdir(); (root / 'build').mkdir()
    shutil.copyfile(a.source / 'gen/sources.gni', root / 'gen/sources.gni')
    (root / '.gn').write_text('buildconfig = "//build/config.gn"\n')
    (root / 'build/config.gn').write_text('set_default_toolchain("//build:host")\n')
    (root / 'build/BUILD.gn').write_text('toolchain("host") { tool("stamp") { command = "touch {{output}}" } }\n')
    (root / 'BUILD.gn').write_text('''import("//gen/sources.gni")
shared = [ "decrepit/blowfish/blowfish.cc", "decrepit/cfb/cfb.cc", "decrepit/ripemd/ripemd.cc" ]
assert(filter_include(crypto_sources, shared) == shared)
assert(filter_include(decrepit_sources, shared) == [])
group("default") {}
''')
    subprocess.run([str(a.gn), 'gen', str(root / 'out'), '--root=' + str(root),
                    '--script-executable=' + str(a.python)], check=True, capture_output=True)
print('common BoringSSL GN source ownership PASS')
