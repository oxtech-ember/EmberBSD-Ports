#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check generated target +BUILD_INFO against the SDK closure guard.

Uses ELF fixtures produced by check-shlibs-origin.py; --pkgsrc is the fresh
export containing the two ELF patches and --fixture is that test's work dir.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'fixture', 'work', 'bmake', 'readelf', 'awk', 'shell', 'sdk-source'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
assert all(value.is_absolute() for value in vars(a).values())
a.work.mkdir()
stage, cross = a.work / 'stage', a.work / 'cross'
shutil.copytree(a.fixture / 'stage space', stage, symlinks=True)
shutil.copytree(a.fixture / 'cross space', cross, symlinks=True)
plist = a.work / 'plist'
info = a.work / '.pkgdb/+BUILD_INFO'
makefile = a.work / 'fixture.mk'
makefile.write_text('''PKGSRCDIR={pkgsrc}
WRKDIR={work}
DESTDIR={stage}
_CROSS_DESTDIR={cross}
PREFIX=/usr/pkg
_PLIST_NOKEYWORDS={plist}
CHECK_SHLIBS_SUPPORTED=yes
USE_CROSS_COMPILE=yes
OBJECT_FMT=ELF
TOOLS_PATH.readelf={readelf}
AWK={awk}
SH={shell}
RUN=@
TEST=test
MKDIR=mkdir -p
ECHO=echo
SORT=sort
CAT=cat
SED=sed
CHMOD=chmod
TRUE=true
DATE=date
UNAME=uname
TYPE=type
PKGSRC_SETENV=env
CHECK_SHLIBS_SKIP=
_OPSYS_SYSTEM_RPATH=
_RRDEPENDS_FILE={depends}
PKG_INFO={pkginfo}
INIT_SYSTEM=none
_USE_NEW_PKGINSTALL=no
.include "${{PKGSRCDIR}}/mk/pkgformat/pkg/metadata.mk"
'''.format(pkgsrc=a.pkgsrc, work=a.work, stage=stage, cross=cross, plist=plist,
           readelf=a.readelf, awk=a.awk, shell=a.shell, depends=a.work/'depends', pkginfo=a.fixture/'pkg-info'))
(a.work/'depends').write_text('full ignored diagnostic-1.0\n')
def build(lines):
    plist.write_text(lines)
    info.unlink(missing_ok=True)
    subprocess.run([str(a.bmake), '-r', '-f', str(makefile), str(info)], check=True)
    result = {}
    for line in info.read_text().splitlines():
        key, sep, value = line.partition('=')
        if sep and key in ('REQUIRES', 'PROVIDES'):
            result.setdefault(key, []).append(value)
    return result
alias_dir = stage / 'usr/pkg/lib/alias-provider'
alias_dir.mkdir(parents=True, exist_ok=True)
alias = alias_dir / 'libdiagnostic.so.1'
alias.unlink(missing_ok=True)
alias.symlink_to('/usr/pkg/lib/external/libdiagnostic.so.1')
a_stable = build('lib/alias-provider/libdiagnostic.so.1\n')
alias.unlink(); alias.symlink_to('/usr/pkg/lib/external/libdiagnostic.so.1.2')
a_physical = build('lib/alias-provider/libdiagnostic.so.1\n')
alias.unlink() # C is a separate package; A's alias is in the target root.
(stage/'usr/pkg/bin').mkdir(parents=True, exist_ok=True)
shutil.copyfile(stage/'usr/pkg/lib/electron44/third-consumer.so', stage/'usr/pkg/bin/third')
c = build('bin/third\n')
assert a_stable['REQUIRES'] == ['/usr/pkg/lib/external/libdiagnostic.so.1'], a_stable
assert a_physical['REQUIRES'] == ['/usr/pkg/lib/external/libdiagnostic.so.1.2'], a_physical
assert c['REQUIRES'] == ['/usr/pkg/lib/alias-provider/libdiagnostic.so.1'], c
sys.path.insert(0, str(a.sdk_source/'src'))
from emberbsd_sdk.binary_release import _check_runtime
from emberbsd_sdk.errors import SDKError
entries = {'C': {'name':'consumer-1', 'node':{'dependencies':['A']}, 'record':c},
           'A': {'name':'alias-1', 'node':{'dependencies':['B']}, 'record':a_stable},
           'B': {'name':'provider-2', 'node':{'dependencies':[]}, 'record':{'PROVIDES':[
               '/usr/pkg/lib/external/libdiagnostic.so.1', '/usr/pkg/lib/external/libdiagnostic.so.1.3']}}}
_check_runtime(None, entries, 'target', set(entries))
entries['A']['record'] = a_physical
try:
    _check_runtime(None, entries, 'target', set(entries))
except SDKError as exc:
    assert 'libdiagnostic.so.1.2' in str(exc), exc
else:
    raise AssertionError('missing physical provider was accepted')
print('PASS: real +BUILD_INFO and SDK closure accept stable and reject missing physical alias')
