#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Query real generated cross wrapper policy.
import os
from pathlib import Path
import shutil
import subprocess
import sys

if len(sys.argv) != 5:
    raise SystemExit('Usage: cross-shell-wrapper-pie-config.py PKGSRC MAKECONF BMAKE NEW_WORK')
source, conf, make = (Path(x).resolve(strict=True) for x in sys.argv[1:4])
work = Path(sys.argv[4])
if not work.is_absolute() or work.exists():
    raise SystemExit('Use a new absolute work path')
work.mkdir()
tree = work / 'pkgsrc'
tree.mkdir()
for entry in source.iterdir():
    if entry.name != 'graphics':
        (tree / entry.name).symlink_to(entry)
(tree / 'graphics').mkdir()
for entry in (source / 'graphics').iterdir():
    if entry.name != 'spirv-cross':
        (tree / 'graphics' / entry.name).symlink_to(entry)
recipe = tree / 'graphics/spirv-cross'
shutil.copytree(source / 'graphics/spirv-cross', recipe)
makefile = recipe / 'Makefile'
text = makefile.read_text()
include = '.include "../../mk/bsd.pkg.mk"'
assert text.count(include) == 1
query = '''post-wrapper:
\t@printf 'WRAPPER_QUERY=%s|%s|%s\\n' '${_PKGSRC_MKPIE}' '${PKGSRC_OVERRIDE_MKPIE}' '${MKPIE_LDFLAGS:UUNSET}'

'''
makefile.write_text(text.replace(include, query + include))
env = os.environ.copy()
env['EMBERBSD_PKGSRCDIR'] = str(tree)
cases = [('on', 'PKGSRC_MKPIE=yes', 'yes|no|-pie'),
         ('off', 'PKGSRC_MKPIE=no', 'no|no|UNSET'),
         ('override', 'PKGSRC_OVERRIDE_MKPIE=yes', 'yes|yes|UNSET')]
for name, setting, expected in cases:
    cmd = [str(make), '-C', str(recipe), 'MAKECONF=' + str(conf),
           'WRKOBJDIR=' + str(work / name), setting, 'wrapper']
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    (work / (name + '.log')).write_text(result.stdout + result.stderr)
    if result.returncode or 'WRAPPER_QUERY=' + expected not in result.stdout:
        raise SystemExit('FAIL: ' + name + '; see ' + str(work / (name + '.log')))
    print('PASS:', name, expected)
