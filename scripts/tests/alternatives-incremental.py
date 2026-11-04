# SPDX-License-Identifier: BSD-2-Clause
"""A changed alternatives.mk must regenerate cached install templates."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

BMAKE, PKGSRC, PATCHED = sys.argv[1:]
with tempfile.TemporaryDirectory(prefix='alternatives-incremental-') as name:
    work = Path(name)
    source = work / 'pkgsrc/mk'
    source.mkdir(parents=True)
    for name in ('pkginstall', 'pkgformat'):
        (source / name).symlink_to(Path(PKGSRC) / 'mk' / name, target_is_directory=True)
    generator = source / 'alternatives.mk'
    old = Path(PATCHED).read_text().replace('${WRKDIR}/.altinstall: ${ALTERNATIVES_SRC} ${PKGSRCDIR}/mk/alternatives.mk', '${WRKDIR}/.altinstall: ${ALTERNATIVES_SRC}').replace('${WRKDIR}/.altdeinstall: ${ALTERNATIVES_SRC} ${PKGSRCDIR}/mk/alternatives.mk', '${WRKDIR}/.altdeinstall: ${ALTERNATIVES_SRC}').replace('@CAT@', '${CAT}').replace('@RM@', '${RM}').replace('@TEST@', '${TEST}')
    generator.write_text(old)
    (work / 'input').write_text('bin/python bin/python3.15\n')
    (work / 'local/sbin').mkdir(parents=True)
    (work / 'host-only').mkdir()
    host_test = work / 'host-only/gtest'
    host_test.write_text('#!/bin/sh\nexec /bin/test "$@"\n')
    host_test.chmod(0o755)
    helper = work / 'local/sbin/pkg_alternatives'
    helper.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$LOG"\n')
    helper.chmod(0o755)
    (work / 'Makefile').write_text(f'''PKGSRCDIR={work}/pkgsrc
PKGDIR={work}/none
WRKDIR={work}
PKG_DB_TMPDIR={work}/meta
LOCALBASE={work}/local
ALTERNATIVES_SRC={work}/input
ECHO=/bin/echo
SED=/usr/bin/sed
CAT=/host-only/gcat
RM=/host-only/grm
TEST={host_test}
MKDIR=/bin/mkdir -p
CHMOD=/bin/chmod
MV=/bin/mv
FILES_SUBST_SED=-e s,@CAT@,/bin/cat,g -e s,@RM@,/bin/rm,g -e s,@TEST@,test,g
.include "{generator}"
INSTALL_SRC=${{PKGSRCDIR}}/mk/pkginstall/header ${{WRKDIR}}/.altinstall
DEINSTALL_SRC=${{PKGSRCDIR}}/mk/pkginstall/header ${{WRKDIR}}/.altdeinstall
.include "${{PKGSRCDIR}}/mk/pkgformat/pkg/scripts.mk"
''')
    def build():
        subprocess.run([BMAKE, '-f', str(work / 'Makefile'), '_pkgformat-generate-install-scripts'],
                       cwd=work, check=True, capture_output=True, text=True)
    build()
    assert '/host-only/gcat' in (work / 'meta/+INSTALL').read_text()
    assert '/host-only/grm' in (work / 'meta/+DEINSTALL').read_text()
    # Model the original build as older than the changed generator.
    older = generator.stat().st_mtime_ns - 2_000_000_000
    for path in (work / '.altinstall', work / '.altdeinstall',
                 work / 'meta/+INSTALL', work / 'meta/+DEINSTALL'):
        os.utime(path, ns=(older, older))
    os.utime(work / 'input', ns=(older - 1_000_000_000, older - 1_000_000_000))
    shutil.copyfile(PATCHED, generator)
    build()
    for filename in ('+INSTALL', '+DEINSTALL'):
        assert '/host-only/' not in (work / 'meta' / filename).read_text(), filename
    env = dict(os.environ, LOG=str(work / 'calls'))
    for filename, stage in [('+INSTALL', 'POST-INSTALL'), ('+DEINSTALL', 'DEINSTALL')]:
        subprocess.run(['/bin/sh', str(work / 'meta' / filename), 'fixture-1.0', stage],
                       cwd=work, env=env, check=True, capture_output=True, text=True)
    assert (work / 'calls').read_text().splitlines() == [
        '-gs register ./+ALTERNATIVES', '-gs unregister ./+ALTERNATIVES']
    assert not (work / '+ALTERNATIVES').exists()
    print('PASS same-work generator refresh and target lifecycle')
