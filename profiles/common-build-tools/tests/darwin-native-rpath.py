#!/usr/bin/env python3
"""Check Darwin native buildlink search and installed runtime path routing."""
import argparse
import shlex
import subprocess
import tempfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--pkgsrc', type=Path, required=True)
p.add_argument('--makeconf', type=Path, required=True)
p.add_argument('--host-prefix', type=Path, required=True)
p.add_argument('--stage-root', type=Path, required=True)
p.add_argument('--sdk-root', type=Path, required=True)
p.add_argument('--target-makeconf', type=Path)
p.add_argument('--baseline-pkgsrc', type=Path)
p.add_argument('--make-arg', action='append', default=[])
a = p.parse_args()

def query(*extra):
    cmd = [str(a.bmake), '-C', str(a.pkgsrc / 'textproc/libcroco'),
           'MAKECONF=' + str(a.makeconf), '_PKGSRC_BARRIER=yes', *a.make_arg,
           *extra, '-V', '${COMPILER_RPATH_FLAG}', '-V', '${_USE_RPATH}',
           '-V', '${BUILDLINK_LDFLAGS}']
    return subprocess.check_output(cmd, text=True).splitlines()

modern = query()
assert modern[0:2] == ['-Wl,-rpath,', 'yes'], modern
flags = shlex.split(modern[2])
hostlib = str(a.host_prefix / 'lib')
physical = str(a.stage_root / str(a.host_prefix).lstrip('/') / 'lib')
assert '-L' + physical in flags, flags
rpaths = [item[len('-Wl,-rpath,'):] for item in flags if item.startswith('-Wl,-rpath,')]
assert hostlib in rpaths, rpaths
assert not any(path.startswith(str(a.stage_root) + '/') or path.startswith(str(a.sdk_root) + '/') for path in rpaths), rpaths
override = shlex.split(query('BUILDLINK_PREFIX.glib2=' + str(a.host_prefix))[2])
assert '-L' + hostlib in override and '-Wl,-rpath,' + hostlib in override, override
legacy = query('OPSYS_VERSION=100400')
assert legacy[0:2] == ['-L', 'no'], legacy
if a.baseline_pkgsrc:
    baseline = subprocess.check_output([str(a.bmake), '-C', str(a.baseline_pkgsrc / 'textproc/libcroco'),
        'MAKECONF=' + str(a.makeconf), '_PKGSRC_BARRIER=yes', *a.make_arg,
        'OPSYS_VERSION=100400', '-V', '${COMPILER_RPATH_FLAG}', '-V', '${_USE_RPATH}',
        '-V', '${BUILDLINK_LDFLAGS}'], text=True).splitlines()
    assert legacy == baseline, (legacy, baseline)
with tempfile.TemporaryDirectory() as tmp:
    makefile = Path(tmp) / 'cross-darwin.mk'
    makefile.write_text('OPSYS_VERSION= 270001\nUSE_CROSS_COMPILE= yes\n.include "' + str(a.pkgsrc / 'mk/platform/Darwin.mk') + '"\n')
    cross = subprocess.check_output([str(a.bmake), '-r', '-f', str(makefile),
                                     '-V', '${_OPSYS_COMPILER_RPATH_FLAG}',
                                     '-V', '${_USE_RPATH}'], text=True).splitlines()
    assert cross == ['-L', 'no'], cross
if a.target_makeconf:
    target = subprocess.check_output([str(a.bmake), '-C', str(a.pkgsrc / 'devel/gettext-tools'),
        'MAKECONF=' + str(a.target_makeconf), '_PKGSRC_BARRIER=yes',
        '-V', '${OPSYS}', '-V', '${COMPILER_RPATH_FLAG}', '-V', '${_USE_RPATH}',
        '-V', '${BUILDLINK_ABI_DEPENDS.libcroco}'], text=True).splitlines()
    assert target == ['NetBSD', '-Wl,-R', 'yes', 'libcroco>=0.6.13nb18'], target
print('PASS: native stage routing, legacy Darwin and selected target flags')
