#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the real FFmpeg option branches with an isolated metadata fixture."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', required=True, type=Path)
args = parser.parse_args()
source = Path(__file__).resolve().parents[3] / 'pkgsrc/multimedia/ffmpeg9/options.mk'
text = source.read_text()
with tempfile.TemporaryDirectory(prefix='ffmpeg-dav1d-options-') as directory:
    root = Path(directory)
    package = root / 'multimedia/ffmpeg9'
    package.mkdir(parents=True)
    (package / 'options.mk').write_text(text)
    for include in re.findall(r'^\.include "\.\./\.\./([^\"]+)"', text, re.M):
        path = root / include
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('DEPENDENCIES+= ' + include + '\n' if include.endswith('buildlink3.mk') else '')
    makefile = root / 'Makefile'
    makefile.write_text('OPSYS=Darwin\nVDPAU_AVAILABLE=no\nVAAPI_AVAILABLE=no\n.include "' + str(package / 'options.mk') + '"\n')
    def query(options):
        result = subprocess.run([str(args.bmake), '-r', '-f', str(makefile), '-V', '${CONFIGURE_ARGS}',
                                 '-V', '${DEPENDENCIES}', '-V', '${PKG_SUGGESTED_OPTIONS}',
                                 'PKG_OPTIONS=' + options], check=True, capture_output=True, text=True)
        flags, deps, defaults = result.stdout.splitlines()
        return flags.split(), deps.split(), defaults.split()
    for selected in ('aom', 'rav1e', 'dav1d'):
        flags, deps, defaults = query(selected)
        assert '--enable-libdav1d' in flags and 'multimedia/dav1d/buildlink3.mk' in deps
        assert 'dav1d' not in defaults
        if selected == 'dav1d':
            assert '--disable-libaom' in flags and '--disable-librav1e' in flags
            assert 'multimedia/libaom/buildlink3.mk' not in deps
            assert 'multimedia/rav1e/buildlink3.mk' not in deps
    flags, deps, _ = query('')
    assert '--disable-libdav1d' in flags and 'multimedia/dav1d/buildlink3.mk' not in deps
    # Evaluate the actual consumer buildlink branches too.  A dav1d-only
    # package must expose the library to its buildlink consumers.
    buildlink = source.with_name('buildlink3.mk').read_text()
    (package / 'buildlink3.mk').write_text(buildlink)
    for include in re.findall(r'^\.\s*include "\.\./\.\./([^\"]+)"', buildlink, re.M):
        path = root / include
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('DEPENDENCIES+= ' + include + '\n' if include.endswith('buildlink3.mk') else '')
    makefile.write_text('.include "' + str(package / 'buildlink3.mk') + '"\n')
    for selected in ('aom', 'rav1e', 'dav1d', ''):
        result = subprocess.run([str(args.bmake), '-r', '-f', str(makefile),
                                 '-V', '${DEPENDENCIES}',
                                 'PKG_BUILD_OPTIONS.ffmpeg9=' + selected],
                                check=True, capture_output=True, text=True)
        assert ('multimedia/dav1d/buildlink3.mk' in result.stdout.split()) == bool(selected)

print('FFmpeg dav1d option metadata passed')
