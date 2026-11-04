#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the actual empty-provider buildlink refresh target."""
import argparse
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', type=Path, required=True)
parser.add_argument('--fragment', type=Path, required=True)
parser.add_argument('--barrier', type=Path, help='actual bsd.pkg.barrier.mk (default: sibling mk directory)')
args = parser.parse_args()
source = args.fragment.read_text()
start = source.index('# Refresh a previously builtin provider')
end = source.index('\n.PHONY: buildlink-${_pkg_}-message', start)
block = source[start:end]
pre_start = source.index('# Register public refresh targets before the pkgsrc barrier.')
pre_end = source.index('\n###\n### BEGIN: after the barrier', pre_start)
entry = source[pre_start:pre_end]
barrier = args.barrier or args.fragment.parent.parent / 'bsd.pkg.barrier.mk'
assert barrier.is_file(), barrier


with tempfile.TemporaryDirectory(prefix='refresh-link-') as temporary:
    root = Path(temporary)
    cookie = root / 'expat.cookie'
    provider = root / 'provider.h'
    provider.write_text('provider')
    link = root / 'expat.h'
    (root / 'Makefile').write_text(
        'RUN=\nRM=/bin/rm\nERROR_MSG=echo\nRECURSIVE_MAKE=' + str(args.bmake) + '\n'
        'USE_BUILTIN.expat?=no\n_BLNK_COOKIE.expat=' + str(cookie) + '\n'
        '.for _pkg_ in expat\n' + block + '\n.endfor\n'
        '.PHONY: buildlink-expat\nbuildlink-expat:\n'
        '\t/bin/ln -s ' + str(provider) + ' ' + str(link) + '\n'
        '\tprintf linked > ' + str(cookie) + '\n')

    def run(*arguments):
        return subprocess.run([str(args.bmake), '-r', '-C', str(root), *arguments],
                              capture_output=True, text=True)

    cookie.write_text('')
    result = run('refresh-empty-buildlink-expat')
    assert result.returncode == 0, result.stdout + result.stderr
    assert link.is_symlink() and link.resolve() == provider.resolve()
    assert cookie.read_text() == 'linked'
    result = run('refresh-empty-buildlink-expat')
    assert result.returncode != 0
    assert cookie.read_text() == 'linked' and link.is_symlink()
    cookie.write_text('')
    result = run('USE_BUILTIN.expat=yes', 'refresh-empty-buildlink-expat')
    assert result.returncode != 0
    assert cookie.read_text() == '' and link.is_symlink()
print('PASS: empty cookie refreshes; nonempty and builtin provider are rejected intact')

# Exercise the real pkgsrc barrier, including its preconditions and recursive
# post-barrier invocation. The controlled provider stands in for buildlink.
with tempfile.TemporaryDirectory(prefix='refresh-barrier-') as temporary:
    root = Path(temporary)
    cookie, link, provider = root / 'expat.cookie', root / 'expat.h', root / 'provider.h'
    events = root / 'events'
    provider.write_text('provider')
    cookie.write_text('')
    (root / 'Makefile').write_text(
        'RUN=\nTEST=/bin/test\nMKDIR=/bin/mkdir -p\nECHO=echo\nRM=/bin/rm\n'
        'ERROR_MSG=echo\nPHASE_MSG=echo\nPKG_INFO=/usr/bin/false\n'
        'WRKDIR=' + str(root) + '\nPKGNAME=fixture-1\nMAKE_JOBS=1\n'
        'RECURSIVE_MAKE=' + str(args.bmake) + ' -r -f ' + str(root / 'Makefile') + '\n'
        'USE_BUILTIN.expat=no\n_BLNK_PACKAGES=expat\n_BLNK_COOKIE.expat=' + str(cookie) + '\n'
        '.include "' + str(barrier) + '"\n' + entry + '\n'
        '.if defined(_PKGSRC_BARRIER)\n.for _pkg_ in expat\n' + block + '\n.endfor\n'
        '.PHONY: buildlink-expat build\nbuildlink-expat:\n'
        '\t/bin/ln -s ' + str(provider) + ' ' + str(link) + '\n'
        '\tprintf linked > ' + str(cookie) + '\n'
        '\tprintf "refresh\\n" >> ' + str(events) + '\n'
        'build:\n\t/bin/test -L ' + str(link) + '\n'
        '\tprintf "build\\n" >> ' + str(events) + '\n'
        '.else\n.PHONY: build\nbuild: barrier\n.endif\n'
        '.PHONY: checksum-phase makedirs depends error-check\n'
        'checksum-phase makedirs depends:\n\tprintf "%s\\n" ${.TARGET} >> ' + str(events) + '\n'
        'error-check:\n\t@true\n')
    # Even when build is requested first, refresh must precede it after the barrier.
    command = [str(args.bmake), '-r', '-C', str(root), 'build', 'refresh-empty-buildlink-expat']
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert events.read_text().splitlines() == ['checksum-phase', 'makedirs', 'depends', 'refresh', 'build']
    assert cookie.read_text() == 'linked' and link.resolve() == provider.resolve()
    events.unlink()
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0, result.stdout + result.stderr
    assert 'build' not in events.read_text().splitlines()
    assert cookie.read_text() == 'linked' and link.is_symlink()
print('PASS: public refresh runs through real barrier before build and fails closed')
