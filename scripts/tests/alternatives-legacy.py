# SPDX-License-Identifier: BSD-2-Clause
"""Run the actual legacy pkginstall generation rules across a source update."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

BMAKE, PKGSRC, PATCHED_ALTERNATIVES, LEGACY = sys.argv[1:]
with tempfile.TemporaryDirectory(prefix='alternatives-legacy-') as name:
    work = Path(name)
    source = work / 'pkgsrc/mk'
    source.mkdir(parents=True)
    (source / 'pkginstall').symlink_to(Path(PKGSRC) / 'mk/pkginstall', target_is_directory=True)
    generator = source / 'alternatives.mk'
    fixed = Path(PATCHED_ALTERNATIVES).read_text()
    old = fixed.replace('${WRKDIR}/.altinstall: ${ALTERNATIVES_SRC} ${PKGSRCDIR}/mk/alternatives.mk', '${WRKDIR}/.altinstall: ${ALTERNATIVES_SRC}').replace('${WRKDIR}/.altdeinstall: ${ALTERNATIVES_SRC} ${PKGSRCDIR}/mk/alternatives.mk', '${WRKDIR}/.altdeinstall: ${ALTERNATIVES_SRC}').replace('@CAT@', '${CAT}').replace('@RM@', '${RM}').replace('@TEST@', '${TEST}')
    generator.write_text(old)
    (work / 'input').write_text('bin/python bin/python3.15\n')
    header = work / 'header'
    shutil.copyfile(Path(PKGSRC) / 'mk/pkginstall/header', header)
    (work / 'local/sbin').mkdir(parents=True)
    (work / 'host-only').mkdir()
    host_test = work / 'host-only/gtest'
    host_test.write_text('#!/bin/sh\nexec /bin/test "$@"\n')
    host_test.chmod(0o755)
    helper = work / 'local/sbin/pkg_alternatives'
    helper.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$LOG"\n')
    helper.chmod(0o755)
    legacy = Path(LEGACY).read_text()
    start = legacy.index('DEINSTALL_FILE=\t\t${PKG_DB_TMPDIR}/+DEINSTALL')
    end = legacy.index('# rc.d scripts', start)
    rules = legacy[start:end]
    (work / 'Makefile').write_text(f'''PKGSRCDIR={work}/pkgsrc
PKGDIR={work}/none
WRKDIR={work}
PKG_DB_TMPDIR={work}/meta
_PKGINSTALL_DIR={work}/pkginstall
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
CMP=/usr/bin/cmp
CP=/bin/cp
TRUE=true
SH=/bin/sh
FILES_SUBST_SED=-e s,@CAT@,/bin/cat,g -e s,@RM@,/bin/rm,g -e s,@TEST@,test,g
.include "{generator}"
_INSTALL_TEMPLATES_DFLT={header}
_DEINSTALL_TEMPLATES_DFLT={header}
INSTALL_SRC={header} ${{WRKDIR}}/.altinstall
DEINSTALL_SRC={header} ${{WRKDIR}}/.altdeinstall
{rules}
''')
    def build():
        subprocess.run([BMAKE, '-f', str(work / 'Makefile'), 'generate-install-scripts'],
                       cwd=work, check=True, capture_output=True, text=True)
    build()
    install = work / 'meta/+INSTALL'
    uninstall = work / 'meta/+DEINSTALL'
    assert '/host-only/gcat' in install.read_text()
    assert '/host-only/grm' in uninstall.read_text()
    with install.open('a') as stream:
        stream.write('# ICON_THEME: keep-on-no-change\n')
    first = install.read_bytes()
    build()
    assert install.read_bytes() == first, 'unchanged generator lost later metadata'
    older = generator.stat().st_mtime_ns - 2_000_000_000
    for path in (work / '.altinstall', work / '.altdeinstall', install, uninstall,
                 work / 'pkginstall/INSTALL', work / 'pkginstall/DEINSTALL'):
        os.utime(path, ns=(older, older))
    os.utime(work / 'input', ns=(older - 1_000_000_000, older - 1_000_000_000))
    shutil.copyfile(PATCHED_ALTERNATIVES, generator)
    build()
    for script in (install, uninstall):
        content = script.read_text()
        assert '/host-only/' not in content, script.name
        assert content.count('#!@SH@') == 1, 'generated base duplicated'
    env = dict(os.environ, LOG=str(work / 'calls'))
    for script, stage in ((install, 'POST-INSTALL'), (uninstall, 'DEINSTALL')):
        subprocess.run(['/bin/sh', str(script), 'fixture-1.0', stage], cwd=work,
                       env=env, check=True, capture_output=True, text=True)
    assert (work / 'calls').read_text().splitlines() == [
        '-gs register ./+ALTERNATIVES', '-gs unregister ./+ALTERNATIVES']
    # A generator transition back to the default must remove obsolete hooks.
    makefile = work / 'Makefile'
    content = makefile.read_text().replace('INSTALL_SRC=' + str(header) + ' ' + str(work) + '/.altinstall',
                                           'INSTALL_SRC=' + str(header)).replace(
        'DEINSTALL_SRC=' + str(header) + ' ' + str(work) + '/.altdeinstall',
        'DEINSTALL_SRC=' + str(header))
    # The f-string writes make-variable references; replace those as well.
    content = content.replace('INSTALL_SRC=' + str(header) + ' ${WRKDIR}/.altinstall',
                              'INSTALL_SRC=' + str(header)).replace(
        'DEINSTALL_SRC=' + str(header) + ' ${WRKDIR}/.altdeinstall',
        'DEINSTALL_SRC=' + str(header))
    makefile.write_text(content)
    older = header.stat().st_mtime_ns - 2_000_000_000
    for path in (install, uninstall, work / 'pkginstall/INSTALL', work / 'pkginstall/DEINSTALL'):
        os.utime(path, ns=(older, older))
    build()
    assert '+ALTERNATIVES' not in install.read_text(), 'removed install hook survived'
    assert '+ALTERNATIVES' not in uninstall.read_text(), 'removed deinstall hook survived'

    # A failed generator must leave the existing intermediate intact.
    intermediate = work / 'pkginstall/INSTALL'
    previous = intermediate.read_bytes()
    stamp = header.stat().st_mtime_ns - 2_000_000_000
    os.utime(intermediate, ns=(stamp, stamp))
    bad_sed = work / 'bad-sed'
    bad_sed.write_text('#!/bin/sh\nexit 1\n')
    bad_sed.chmod(0o755)
    result = subprocess.run([BMAKE, '-f', str(makefile), str(intermediate), 'SED=' + str(bad_sed)],
                            cwd=work, capture_output=True, text=True)
    assert result.returncode != 0, 'failed generator unexpectedly succeeded'
    assert intermediate.read_bytes() == previous, 'failed generator damaged previous intermediate'
    print('PASS legacy refresh, unchanged late data, default transition, atomic failure and target lifecycle')
