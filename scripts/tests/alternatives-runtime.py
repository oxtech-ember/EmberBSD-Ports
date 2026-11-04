# SPDX-License-Identifier: BSD-2-Clause
"""Exercise pkgsrc's actual alternatives and script generation rules."""
from pathlib import Path
import subprocess
import sys
import tempfile

BMAKE, PKGSRC, ALTERNATIVES = sys.argv[1:]
with tempfile.TemporaryDirectory(prefix='alternatives-runtime-') as name:
    work = Path(name)
    (work / 'input').write_text('bin/python bin/python3.15\n')
    (work / 'local/sbin').mkdir(parents=True)
    (work / 'host-only').mkdir()
    host_test = work / 'host-only/gtest'
    host_test.write_text('#!/bin/sh\nexec /bin/test "$@"\n')
    host_test.chmod(0o755)
    helper = work / 'local/sbin/pkg_alternatives'
    helper.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$LOG"\n')
    helper.chmod(0o755)
    makefile = f'''PKGSRCDIR={PKGSRC}
PKGDIR={work}/none
WRKDIR={work}
PKG_DB_TMPDIR={work}/meta
LOCALBASE={work}/local
ALTERNATIVES_SRC={work}/input
ECHO=/bin/echo
SED=/usr/bin/sed
CAT=/host-only/gcat
RM=/host-only/grm
TEST={work}/host-only/gtest
MKDIR=/bin/mkdir -p
CHMOD=/bin/chmod
MV=/bin/mv
FILES_SUBST_SED=-e s,@CAT@,/bin/cat,g -e s,@RM@,/bin/rm,g -e s,@TEST@,test,g
.include "{ALTERNATIVES}"
INSTALL_SRC=${{PKGSRCDIR}}/mk/pkginstall/header ${{WRKDIR}}/.altinstall
DEINSTALL_SRC=${{PKGSRCDIR}}/mk/pkginstall/header ${{WRKDIR}}/.altdeinstall
.include "${{PKGSRCDIR}}/mk/pkgformat/pkg/scripts.mk"
'''
    (work / 'Makefile').write_text(makefile)
    subprocess.run([BMAKE, '-f', str(work / 'Makefile'), '_pkgformat-generate-install-scripts'],
                   cwd=work, check=True, capture_output=True, text=True)
    import os
    env = dict(os.environ, LOG=str(work / 'calls'))
    for filename, stage in [('+INSTALL', 'POST-INSTALL'), ('+DEINSTALL', 'DEINSTALL')]:
        script = work / 'meta' / filename
        assert '/host-only/' not in script.read_text(), filename
        subprocess.run(['/bin/sh', str(script), 'fixture-1.0', stage], cwd=work,
                       env=env, check=True, capture_output=True, text=True)
        if stage == 'POST-INSTALL':
            assert (work / '+ALTERNATIVES').read_text() == 'bin/python bin/python3.15\n'
        else:
            assert not (work / '+ALTERNATIVES').exists()
    assert (work / 'calls').read_text().splitlines() == [
        '-gs register ./+ALTERNATIVES', '-gs unregister ./+ALTERNATIVES']
    print('PASS actual pkgsrc generation and register/unregister lifecycle')
