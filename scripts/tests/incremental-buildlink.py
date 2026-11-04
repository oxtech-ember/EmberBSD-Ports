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
args = parser.parse_args()
source = args.fragment.read_text()
start = source.index('# Refresh a previously builtin provider')
end = source.index('\n.PHONY: buildlink-${_pkg_}-message', start)
block = source[start:end]

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
