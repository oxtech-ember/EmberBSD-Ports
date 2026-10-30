#!/usr/bin/env python3
# $NetBSD$
# Origin: EmberBSD (AI-assisted). Regression test: meinproc6 copied into a
# new prefix must read the KDocTools data of that prefix without --srcdir.
#
# usage: relocated-data.py PREFIX [LAUNCHER ...]
# PREFIX holds bin/meinproc6 and share/kf6/kdoctools. A launcher, if given,
# runs the copied tool (for example a runtime loader on Darwin).
import os, shutil, subprocess, sys, tempfile

if len(sys.argv) < 2:
    raise SystemExit('usage: relocated-data.py PREFIX [LAUNCHER ...]')
prefix, launcher = os.path.abspath(sys.argv[1]), sys.argv[2:]
with tempfile.TemporaryDirectory(prefix='kdoctools-relocated-') as tmp:
    moved = os.path.join(tmp, 'prefix')
    os.makedirs(os.path.join(moved, 'bin'))
    shutil.copy2(os.path.join(prefix, 'bin/meinproc6'), os.path.join(moved, 'bin'))
    if os.path.isdir(os.path.join(prefix, 'lib')):
        os.symlink(os.path.join(prefix, 'lib'), os.path.join(moved, 'lib'))
    shutil.copytree(os.path.join(prefix, 'share/kf6/kdoctools'),
                    os.path.join(moved, 'share/kf6/kdoctools'), symlinks=True)
    doc = os.path.join(tmp, 'index.docbook')
    with open(doc, 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<article lang="en"><title>Relocated</title>'
                '<para>KDocTools data from the selected prefix.</para></article>\n')
    env = dict(os.environ, HOME=tmp, XDG_DATA_DIRS=os.path.join(tmp, 'none'),
               XDG_DATA_HOME=os.path.join(tmp, 'none'))
    r = subprocess.run(launcher + [os.path.join(moved, 'bin/meinproc6'), '--stdout', doc],
                       cwd=tmp, env=env, capture_output=True, text=True)
    if r.returncode or 'Unable to find' in r.stderr or 'Relocated' not in r.stdout:
        sys.stderr.write(r.stderr)
        raise SystemExit('FAIL: relocated meinproc6 did not use its own prefix data')
print('PASS: relocated meinproc6 reads its own prefix data')
