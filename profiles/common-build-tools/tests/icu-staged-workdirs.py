#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise pkgsrc ICU configure cookies with two explicit host tool paths.

Caller coordinates shared prefix/stage and exclusive work-directory locks.
"""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'makefiles', 'pkgsrc', 'makeconf', 'cross-tools', 'stage', 'work', 'distdir'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
for path in vars(a).values():
    if not path.is_absolute():
        p.error('all paths must be absolute')
if a.work.exists():
    p.error('work must not already exist')
a.work.mkdir(parents=True)
alias = a.work / 'staged tools alias'
alias.symlink_to(a.stage, target_is_directory=True)
obj = a.work / 'objects'
env = dict(os.environ, MAKECONF=str(a.makeconf), PYTHONDONTWRITEBYTECODE='1')
base = [str(a.bmake), '-m', str(a.makefiles), '-C', str(a.pkgsrc / 'textproc/icu'),
        'EMBERBSD_CROSS_TOOLS=' + str(a.cross_tools), 'WRKOBJDIR=' + str(obj),
        'DISTDIR=' + str(a.distdir), 'SKIP_DEPENDS=yes']

def run(stage, *args, success=True):
    result = subprocess.run(base + ['ICU_STAGED_HOST_PREFIX=' + str(stage), *args], env=env,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if (result.returncode == 0) != success:
        raise RuntimeError(result.stdout)
    return result.stdout

workdirs = []
for stage in (a.stage, alias):
    run(stage, 'configure')
    path = Path(run(stage, '-V', '${WRKDIR}').strip())
    if not (path / '.configure_done').is_file() or not (path / '.icu-host-stage-key').is_file():
        raise RuntimeError('missing configured stage identity')
    workdirs.append(path)
if workdirs[0] == workdirs[1]:
    raise RuntimeError('two stages shared a work directory')
if run(a.stage, 'configure').strip():
    raise RuntimeError('unchanged stage unexpectedly reconfigured')
marker = workdirs[0] / '.icu-host-stage-key'
old = marker.read_bytes()
try:
    marker.write_text('0' * 64 + '\n')
    if 'stage hash collision' not in run(a.stage, 'configure', success=False):
        raise RuntimeError('stage collision was not rejected')
finally:
    marker.write_bytes(old)
if 'stage-keyed work directory' not in run(a.stage, 'WRKDIR=' + str(a.work / 'forced'),
                                           'configure', success=False):
    raise RuntimeError('explicit work override was not rejected')
print('PASS: staged ICU configure, no-op and collision controls')
