#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check gzip bootstrap metadata and the real Info provider lifecycle."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
for argument in ('bmake', 'makefiles', 'makeconf', 'pkgsrc', 'install-info', 'host-prefix'):
    p.add_argument('--' + argument, required=True, type=Path)
p.add_argument('--makefile', type=Path, help='optional trial recipe; defaults to the exported gzip Makefile')
a = p.parse_args()
package = a.pkgsrc / 'archivers/gzip'
makefile = a.makefile or package / 'Makefile'
assert 'info/gzip.info' in (package / 'PLIST').read_text().splitlines()
with tempfile.TemporaryDirectory(prefix='gzip-phase-check-') as tmp:
    root = Path(tmp)
    def query(label, *, bootstrap, override=None):
        cmd = [str(a.bmake), '-m', str(a.makefiles), '-f', str(makefile),
               'SHELL=' + str(a.host_prefix / 'bin/mksh'),
               'MAKECONF=' + (str(a.makeconf) if bootstrap else '/dev/null'),
               'LOCALBASE=' + str(a.host_prefix),
               'PKG_DBDIR=' + str(a.host_prefix / 'pkgdb'),
               'PKG_TOOLS_BIN=' + str(a.host_prefix / 'sbin'),
               'WRKOBJDIR=' + str(root / label)]
        if bootstrap:
            cmd.append('EMBERBSD_DARWIN_BOOTSTRAP=yes')
        if override is not None:
            cmd.append('EMBERBSD_GZIP_DEFER_INFO=' + override)
        cmd += ['-V', '${INFO_FILES:Uunset}', '-V', '${EMBERBSD_GZIP_DEFER_INFO:Uunset}',
                '-V', '${INSTALL_INFO:Uunset}', '-V', '${DEPENDS}']
        return subprocess.check_output(cmd, cwd=package, text=True).splitlines()
    initial = query('initial', bootstrap=True)
    full = query('full', bootstrap=True, override='no')
    ordinary = query('ordinary', bootstrap=False)
    assert initial[0:2] == ['unset', 'yes'] and 'pkg_install-info' not in initial[3], initial
    assert full[0:2] == ['yes', 'no'] and full[2] == str(a.install_info), full
    assert 'pkg_install-info-[0-9]*:../../pkgtools/pkg_install-info' in full[3], full
    assert ordinary[0:2] == ['yes', 'no'] and 'pkg_install-info' in ordinary[3], ordinary
    infodir = root / 'info'
    infodir.mkdir()
    info = infodir / 'fixture.info'
    info.write_text('INFO-DIR-SECTION Utilities\nSTART-INFO-DIR-ENTRY\n'
                    '* EmberGzipFixture: (fixture). Test registration.\n'
                    'END-INFO-DIR-ENTRY\n\x1f\nFile: fixture.info, Node: Top\n')
    cmd = [str(a.install_info), '--info-dir=' + str(infodir), str(info)]
    for _ in range(2):
        subprocess.run(cmd, check=True, capture_output=True)
    index = infodir / 'dir'
    assert index.read_text().count('* EmberGzipFixture:') == 1
    subprocess.run(cmd[:-1] + ['--delete', str(info)], check=True, capture_output=True)
    assert not index.exists() or '* EmberGzipFixture:' not in index.read_text()
print('PASS: bootstrap default, explicit full, ordinary default, retained Info and add/repeat/remove')
