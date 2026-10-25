#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted glib2 Darwin Objective-C regression.
"""Configure the patched glib Darwin block with real meson, with and without objc."""
import argparse
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--meson', required=True, type=Path)
parser.add_argument('--distfile', required=True, type=Path, help='glib-*.tar.xz')
parser.add_argument('--patch', default=Path('/usr/bin/patch'), type=Path)
parser.add_argument('--objc', type=Path, help='a working Objective-C compiler, optional')
parser.add_argument('--work-parent', required=True, type=Path)
a = parser.parse_args()
recipe = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory(prefix='glib2-objc-', dir=a.work_parent) as temporary:
    root = Path(temporary)
    with tarfile.open(a.distfile) as archive:
        member = next(m for m in archive.getmembers() if m.name.count('/') == 1
                      and m.name.endswith('/meson.build'))
        (root / 'meson.build').write_bytes(archive.extractfile(member).read())
    subprocess.run([str(a.patch), '-s', '-F0', 'meson.build',
                    str(recipe / 'patches/patch-meson.build')], cwd=root, check=True)
    lines = (root / 'meson.build').read_text().splitlines()
    first = lines.index('osx_ldflags = []')
    # The Darwin block ends at the first column-0 endif that closes the objc branch.
    cocoa = next(i for i in range(first, len(lines)) if 'HAVE_COCOA' in lines[i])
    last = next(i for i in range(cocoa, len(lines)) if lines[i] == 'endif')
    block = '\n'.join(lines[first:last + 1])

    def configure(name, system, subsystem, objc):
        project = root / name
        project.mkdir()
        (project / 'meson.options').write_text(
            "option('use_cocoa', type : 'boolean', value : false)\n")
        (project / 'meson.build').write_text(
            "project('glib-objc-fixture', meson_version : '>= 1.1')\n"
            f"host_system = '{system}'\nsubsystem = '{subsystem}'\n"
            "glib_conf = configuration_data()\n" + block + "\n"
            "message('RESULT carbon=@0@ cocoa=@1@ ldflags=@2@'.format("
            "glib_have_carbon, glib_have_cocoa, osx_ldflags))\n")
        environment = {name: os.environ[name] for name in ('PATH', 'HOME', 'TMPDIR')
                       if name in os.environ}
        environment['OBJC'] = str(objc)
        done = subprocess.run([str(a.meson), 'setup', str(project / 'out'), str(project)],
                              env=environment, text=True, capture_output=True, timeout=120)
        return done.returncode, done.stdout + done.stderr

    missing = root / 'no-such-objc'
    rc, out = configure('macos-no-objc', 'darwin', 'macos', missing)
    assert rc == 0, out
    assert 'RESULT carbon=false cocoa=false ldflags=[]' in out, out
    assert 'building without the Carbon and Cocoa backends' in out, out
    rc, out = configure('other-os', 'netbsd', '', missing)
    assert rc == 0 and 'RESULT carbon=false cocoa=false' in out, out
    assert 'Carbon and Cocoa backends' not in out, out
    checks = 2
    if a.objc:
        rc, out = configure('macos-objc', 'darwin', 'macos', a.objc)
        assert rc == 0 and 'Mac OS X Carbon support' in out, out
        assert 'Carbon and Cocoa backends' not in out, out
        checks += 1
print(f'PASS: {checks} glib Darwin objc configurations with real meson')
