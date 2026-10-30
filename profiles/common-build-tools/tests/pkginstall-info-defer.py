#!/usr/bin/env python3
"""Exercise a generated package hook when its selected cat is unavailable."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('package', 'bsdtar', 'shell'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
script = subprocess.check_output([a.bsdtar, '-xOf', a.package, '+INSTALL'], text=True)
assert '# INFO:' in script and 'selected tools for +INFO_FILES are unavailable' in script
with tempfile.TemporaryDirectory(prefix='pkginstall-info-defer-') as tmp:
    work = Path(tmp)
    lines = script.splitlines(keepends=True)
    lines = [('CAT="' + str(work / 'missing-cat') + '"\n') if line.startswith('CAT=') else line
             for line in lines]
    hook = work / '+INSTALL'
    hook.write_text(''.join(lines))
    env = dict(os.environ, PKG_METADATA_DIR=str(work))
    pre = subprocess.run([a.shell, str(hook), 'coreutils-9.12', 'PRE-INSTALL'],
                         cwd=work, env=env, text=True, capture_output=True)
    assert pre.returncode == 0 and not (work / '+INFO_FILES').exists(), pre.stderr
    post = subprocess.run([a.shell, str(hook), 'coreutils-9.12', 'POST-INSTALL'],
                          cwd=work, env=env, text=True, capture_output=True)
    assert post.returncode != 0 and 'selected tools for +INFO_FILES are unavailable' in post.stderr, post.stderr
print('PASS: PRE defers missing selected tool; POST fails closed if still unavailable')
