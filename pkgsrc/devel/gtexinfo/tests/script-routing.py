#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check installed Texinfo shell scripts and selected awk routing."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--root', type=Path, required=True, help='physical installed package prefix')
p.add_argument('--shell', required=True)
p.add_argument('--awk', required=True)
p.add_argument('--native-prefix', type=Path, help='run host scripts with this selected prefix')
a = p.parse_args()
root = a.root.resolve(strict=True)
scripts = [root / 'bin/texindex', root / 'bin/texi2dvi', root / 'bin/texi2pdf',
           root / 'bin/pdftexi2dvi', root / 'share/texinfo/info-hooks/manual-not-found']
for script in scripts:
    assert script.read_text().splitlines()[0] == '#!' + a.shell, script
assert 'awk_binary="' + a.awk + '"' in scripts[0].read_text()
assert 'AWK=' + a.awk in scripts[-1].read_text()
if a.native_prefix:
    prefix = a.native_prefix.resolve(strict=True)
    with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
        fake_man = Path(tmp) / 'man'
        fake_man.write_text('#!' + a.shell + '\nexit 1\n')
        fake_man.chmod(0o755)
        env = dict(os.environ, PATH=tmp + ':' + str(prefix / 'bin') + ':' + str(prefix / 'gnu/bin'),
                   TEXINDEX_SCRIPT=str(root / 'share/texinfo/texindex.awk'))
        env.pop('TEXINDEX_AWK', None)
        result = subprocess.run([str(scripts[0]), '--version'], env=env, capture_output=True, text=True)
        assert result.returncode == 0 and 'texindex' in result.stdout, (result.stdout, result.stderr)
        result = subprocess.run([str(scripts[-1]), 'autoconf'], env=env, capture_output=True, text=True)
        assert result.returncode == 0 and 'autoconf/manual' in result.stdout, (result.stdout, result.stderr)
print('Texinfo script shell and awk routing: PASS')
