#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check AutoGen's cat selection with the selected host shell."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--shell', type=Path, required=True)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--cat', type=Path, required=True)
parser.add_argument('--printf', type=Path, required=True)
parser.add_argument('--chmod', type=Path, required=True)
args = parser.parse_args()
source = (args.source / 'autoopts/mk-tpl-config.sh').read_text()
function = source[source.index('find_cat_prog() {'):source.index('\nscan_cflags() {')]
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bindir = root / 'bin'
    bindir.mkdir()
    (bindir / 'cat').symlink_to(args.cat.resolve())
    (bindir / 'printf').symlink_to(args.printf.resolve())
    (bindir / 'chmod').symlink_to(args.chmod.resolve())
    env = dict(os.environ, PATH=str(bindir))
    script = "die() { echo \"$*\" >&2; exit 1; }\n" + function + '\nPOSIX_SHELL="$1"\nfind_cat_prog\n'
    good = subprocess.run([str(args.shell), '-c', script, 'test', str(args.shell)], cwd=root, env=env, capture_output=True, text=True)
    assert good.returncode == 0, good.stderr
    assert str(bindir / 'cat') in (root / 'man2man').read_text()
    (bindir / 'cat').unlink()
    bad = subprocess.run([str(args.shell), '-c', script, 'test', str(args.shell)], cwd=root, env=env, capture_output=True, text=True)
    assert bad.returncode != 0 and "cannot locate 'cat'" in bad.stderr, bad.stderr
print('selected cat and missing cat: PASS')
