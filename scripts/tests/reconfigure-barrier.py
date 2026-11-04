#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise public reconfigure through real pkgsrc phase/barrier fragments."""
import argparse
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', type=Path, required=True)
parser.add_argument('--pkgsrc', type=Path, required=True)
args = parser.parse_args()
mk = args.pkgsrc / 'mk'
configure = (mk / 'configure/configure.mk').read_text()
part = configure[configure.index('_CONFIGURE_TARGETS+=\tcheck-vulnerable'):configure.index('.PHONY: configure-message')]
bsdconfigure = (mk / 'configure/bsd.configure.mk').read_text()
cookie = bsdconfigure[bsdconfigure.index('# Creates the "configure" cookie file.'):]
build = (mk / 'build/build.mk').read_text()
clean = build[build.index('.PHONY: build-clean'):build.index('######################################################################\n### real-build')]
makevars = (mk / 'bsd.makevars.mk').read_text()
invalidate = makevars[makevars.index('.PHONY: invalidate-makevars'):]
barrier = mk / 'bsd.pkg.barrier.mk'

with tempfile.TemporaryDirectory(prefix='pkgsrc-reconfigure-') as tmp:
    root = Path(tmp)
    work = root / 'work'
    work.mkdir()
    source, obj, events = work / 'source.c', work / 'source.o', root / 'events'
    source.write_text('source\n')
    obj.write_text('object\n')
    before = [(p.stat().st_ino, p.stat().st_mtime_ns) for p in (source, obj)]
    for name in ('extract', 'patch', 'wrapper', 'configure', 'build', 'install', 'package'):
        (work / ('.' + name + '_done')).write_text('fixture-1\n')
        (work / ('.' + name + '_makevars.mk')).write_text('# stale\n')
    (root / 'Makefile').write_text(
        'RUN=\nRM=/bin/rm\nTEST=/bin/test\nMKDIR=/bin/mkdir -p\nECHO=echo\n'
        'DO_NADA=true\nPHASE_MSG=echo\nERROR_MSG=echo\nFALSE=false\n'
        'PKG_INFO=/usr/bin/false\nPKGNAME=fixture-1\nWRKDIR=' + str(work) + '\n'
        '_CLEANING=0\nMAKE_JOBS=1\nRECURSIVE_MAKE=' + str(args.bmake) + ' -r -f ' + str(root / 'Makefile') + '\n'
        '_COOKIE.configure=${WRKDIR}/.configure_done\n_COOKIE.build=${WRKDIR}/.build_done\n'
        '_ALL_PHASES=extract patch wrapper configure build install package\n'
        '.for _phase_ in ${_ALL_PHASES}\n_MAKEVARS_MK.${_phase_}=${WRKDIR}/.${_phase_}_makevars.mk\n.endfor\n'
        '.if defined(_PKGSRC_BARRIER)\nBUILDLINK_LDFLAGS=-lmp3lame\n.endif\n'
        '.include "' + str(barrier) + '"\n' + part + '\n' + cookie + '\n.if !defined(NO_BUILD)\n' + clean + '\n.endif\n' + invalidate + '\n'
        '.PHONY: install-clean _package-clean checksum-phase makedirs depends error-check acquire-lock release-lock\n'
        'install-clean:\n\t${RM} -f ${WRKDIR}/.install_done\n'
        '_package-clean:\n\t${RM} -f ${WRKDIR}/.package_done\n'
        'checksum-phase makedirs depends:\n\tprintf "%s\\n" ${.TARGET} >> ' + str(events) + '\n'
        'error-check acquire-lock release-lock:\n\t@true\n'
        '.PHONY: check-vulnerable wrapper acquire-configure-lock release-configure-lock '
        'configure-check-interactive configure-message configure-vars pre-configure '
        'do-configure-pre-hook pre-configure-checks-hook do-configure do-configure-post-hook post-configure\n'
        'check-vulnerable wrapper acquire-configure-lock release-configure-lock '
        'configure-check-interactive configure-message configure-vars '
        'do-configure-pre-hook pre-configure-checks-hook do-configure-post-hook:\n\t@true\n'
        'pre-configure post-configure:\n\tprintf "%s\\n" ${.TARGET} >> ' + str(events) + '\n'
        'do-configure:\n\t/bin/test "${FORCE_FAIL:Uno}" != yes\n\t/bin/test "${_PKGSRC_BARRIER:U}" = yes\n'
        '\t/bin/test "${BUILDLINK_LDFLAGS:U}" = -lmp3lame\n'
        '\tprintf "do-configure\\n" >> ' + str(events) + '\n')
    def run(target, *extra):
        return subprocess.run([str(args.bmake), '-r', '-C', str(root), *extra, target], capture_output=True, text=True)
    result = run('reconfigure')
    assert result.returncode == 0, result.stdout + result.stderr
    assert events.read_text().splitlines() == ['checksum-phase', 'makedirs', 'depends', 'pre-configure', 'do-configure', 'post-configure']
    assert (work / '.configure_done').read_text().strip() == 'fixture-1'
    for name in ('build', 'install', 'package'):
        assert not (work / ('.' + name + '_done')).exists()
    for name in ('extract', 'patch', 'wrapper'):
        assert (work / ('.' + name + '_done')).exists()
    assert not list(work.glob('.*_makevars.mk'))
    assert [(p.stat().st_ino, p.stat().st_mtime_ns) for p in (source, obj)] == before
    previous = events.read_text()
    result = run('configure')
    assert result.returncode == 0 and events.read_text() == previous, result.stdout + result.stderr
    result = run('reconfigure', 'FORCE_FAIL=yes')
    assert result.returncode != 0 and not (work / '.configure_done').exists()
    assert [(p.stat().st_ino, p.stat().st_mtime_ns) for p in (source, obj)] == before
    result = run('configure')
    assert result.returncode == 0 and (work / '.configure_done').read_text().strip() == 'fixture-1'
    for name in ('build', 'install', 'package'):
        (work / ('.' + name + '_done')).write_text('fixture-1\n')
    result = run('reconfigure', 'NO_BUILD=yes')
    assert result.returncode == 0, result.stdout + result.stderr
    assert (work / '.configure_done').read_text().strip() == 'fixture-1'
    assert all(not (work / ('.' + n + '_done')).exists() for n in ('build', 'install', 'package'))
    assert [(p.stat().st_ino, p.stat().st_mtime_ns) for p in (source, obj)] == before
print('PASS: reconfigure crosses barrier, retains source/objects, clears later state and configure is then a no-op')
