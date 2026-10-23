#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted real pkgsrc recipe metadata regression.
"""Evaluate the direct recipe with the complete real pkgsrc make framework."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', required=True, type=Path)
parser.add_argument('--pkg-admin', required=True, type=Path)
parser.add_argument('--pkgsrc', required=True, type=Path)
parser.add_argument('--work-parent', required=True, type=Path)
a = parser.parse_args()
recipe = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='editline-recipe-', dir=a.work_parent) as temporary:
    root = Path(temporary)
    tree = root / 'pkgsrc'; tree.mkdir()
    for child in a.pkgsrc.iterdir():
        if child.name != 'devel' and not child.name.startswith('.'):
            (tree / child.name).symlink_to(child)
    (tree / 'devel').mkdir()
    for child in (a.pkgsrc / 'devel').iterdir():
        if child.name != 'editline':
            (tree / 'devel' / child.name).symlink_to(child)
    shutil.copytree(recipe, tree / 'devel/editline')
    sysroot = root / 'sysroot'; sysroot.mkdir()
    marker = sysroot / 'usr/share/emberbsd/ports/editline.distinfo'
    marker.parent.mkdir(parents=True)
    environment = {name: os.environ[name] for name in ('PATH', 'HOME', 'TMPDIR') if name in os.environ}
    checks = 0
    for name, policy, marked, exported, opsys, expected in (
        ('profile-stale-base', True, False, False, 'NetBSD', True),
        ('profile-current-base', True, True, False, 'NetBSD', True),
        ('marked-base-no-profile', False, True, False, 'NetBSD', True),
        ('external-unmarked-system', False, False, False, 'NetBSD', False),
        ('exported-unmarked-base', False, False, True, 'NetBSD', True),
        ('exported-other-os', False, False, True, 'Linux', False),
    ):
        export_marker = tree / 'EMBERBSD-PKGSRC-REVISION'
        if exported:
            export_marker.write_text('fixture\n')
        elif export_marker.exists():
            export_marker.unlink()
        if marked:
            marker.write_bytes((recipe / 'distinfo').read_bytes())
        elif marker.exists():
            marker.unlink()
        command = [str(a.bmake), '-r', '-V', '${PKG_FAIL_REASON}',
                   'MAKECONF=/dev/null', 'OPSYS=' + opsys, 'OS_VERSION=11.0',
                   'HOST_MACHINE_ARCH=aarch64', 'USE_LANGUAGES=', 'USE_LIBTOOL=no',
                   'USE_TOOLS=', 'GCC_REQD=', 'PKG_ADMIN=' + str(a.pkg_admin),
                   'PKG_INFO=/usr/bin/false',
                   'MACHINE_ARCH=aarch64', 'MACHINE_GNU_ARCH=aarch64',
                   'MACHINE_GNU_PLATFORM=aarch64--netbsd',
                   'TOOLS_CROSS_DESTDIR=' + str(sysroot),
                   'EMBERBSD_PORTS=' + ('yes' if policy else 'no')]
        done = subprocess.run(command, cwd=tree / 'devel/editline', env=environment,
                              text=True, capture_output=True, timeout=60)
        if done.returncode:
            raise AssertionError(f'{name}: {done.stderr}')
        refused = 'EmberBSD base provides libedit.' in done.stdout
        assert refused == expected, (name, done.stdout)
        checks += 1
print(f'PASS: {checks} direct recipe selections with the real pkgsrc framework')
