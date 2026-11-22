#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check gzip bootstrap metadata and the real Info provider lifecycle."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

p = argparse.ArgumentParser()
for argument in ('bmake', 'makefiles', 'makeconf', 'pkgsrc', 'install-info', 'host-prefix'):
    p.add_argument('--' + argument, required=True, type=Path)
p.add_argument('--makefile', type=Path, help='optional trial recipe; defaults to the exported gzip Makefile')
p.add_argument('--gzip-build', type=Path, help='configured gzip tree with its built Info file; test its real install target')
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
                '-V', '${INSTALL_INFO:Uunset}', '-V', '${DEPENDS}',
                '-V', '${CONFIGURE_ARGS}', '-V', '${INSTALL_ENV}',
                '-V', '${GNU_CONFIGURE_INFODIR}', '-V', '${USE_TOOLS}']
        return subprocess.check_output(cmd, cwd=package, text=True).splitlines()
    initial = query('initial', bootstrap=True)
    full = query('full', bootstrap=True, override='no')
    ordinary = query('ordinary', bootstrap=False)
    assert initial[0:2] == ['unset', 'yes'] and 'pkg_install-info' not in initial[3], initial
    assert full[0:2] == ['yes', 'no'] and full[2] == str(a.install_info), full
    # An explicitly selected native provider needs no resolver dependency.
    assert 'install-info:run' in full[7].split(), full
    assert ordinary[0:2] == ['yes', 'no'] and 'pkg_install-info' in ordinary[3], ordinary
    for phase in (initial, full, ordinary):
        infodirs = [word for word in shlex.split(phase[4]) if word.startswith('--infodir=')]
        assert infodirs == ['--infodir=' + phase[6]], phase
    assert 'AM_UPDATE_INFO_DIR=no' in shlex.split(initial[5]), initial
    for phase in (full, ordinary):
        assert 'AM_UPDATE_INFO_DIR=no' not in shlex.split(phase[5]), phase

    if a.gzip_build:
        doc = a.gzip_build.resolve() / 'doc'
        source_info = doc / 'gzip.info'
        assert source_info.is_file() and source_info.stat().st_size
        expected_info = source_info.read_bytes()
        trapdir = root / 'trap'
        trapdir.mkdir()
        called = root / 'install-info-called'
        trap = trapdir / 'install-info'
        trap.write_text('#!/bin/sh\nprintf called > ' + shlex.quote(str(called)) + '\nexit 1\n')
        trap.chmod(0o755)
        env = dict(os.environ, PATH=str(trapdir) + os.pathsep + os.environ['PATH'])
        for word in shlex.split(initial[5]):
            name, separator, value = word.partition('=')
            assert separator, word
            env[name] = value
        stage = root / 'stage'
        subprocess.run([str(a.bmake), '-C', str(doc),
                        'DESTDIR=' + str(stage), 'infodir=' + initial[6],
                        'install-info-am'], env=env, check=True, capture_output=True)
        installed = stage / initial[6].lstrip('/')
        assert source_info.read_bytes() == expected_info
        assert (installed / 'gzip.info').read_bytes() == expected_info
        assert not (installed / 'dir').exists()
        assert not called.exists(), 'Automake invoked install-info during deferred installation'
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
print('PASS: bootstrap/full/ordinary metadata, Info destination, deferred registration and provider lifecycle')
