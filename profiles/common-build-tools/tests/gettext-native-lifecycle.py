#!/usr/bin/env python3
"""Exercise offline native payload staging and gettext replacement without scripts.

This checks package payload and metadata only; final native installation runs
package integration scripts separately through ordinary pkg_add.
"""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
for name in ('pkg-add', 'pkg-info', 'pkg-admin', 'root', 'prefix', 'dependency-archives',
             'plain', 'full', 'glib', 'libcroco'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
root = a.root.resolve()
if root.exists():
    raise SystemExit('fixture root must not already exist')
if not a.prefix.is_absolute() or not a.root.is_absolute():
    raise SystemExit('fixture root and logical prefix must be absolute')
root.mkdir(parents=True)
db = root / str(a.prefix).lstrip('/') / 'pkgdb'
db.mkdir(parents=True)
env = dict(os.environ)
env.pop('DYLD_LIBRARY_PATH', None)
env.pop('PKG_PATH', None)
def command(*args):
    return subprocess.check_output([str(x) for x in args], env=env, text=True)
def name(archive):
    lines = command(a.pkg_info, '-qf', archive).splitlines()
    return next(line[6:] for line in lines if line.startswith('@name '))
def dependencies(archive):
    return [line for line in command(a.pkg_info, '-qn', archive).splitlines() if line]
archives = list(dict.fromkeys(path.resolve() for path in
                              [*a.dependency_archives.glob('*.tgz'), a.glib, a.libcroco]))
by_name = {name(path): path for path in archives}
assert len(by_name) == len(archives), 'duplicate provider identities'
plain_name, full_name = name(a.plain), name(a.full)
assert plain_name == full_name == 'gettext-tools-1.0nb7', (plain_name, full_name)
installed = set()
def install(archive):
    package = name(archive)
    if package in installed:
        return
    for pattern in dependencies(archive):
        matches = [n for n in by_name if subprocess.run(
            [str(a.pkg_admin), 'pmatch', pattern, n], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0]
        assert len(matches) == 1, (package, pattern, matches)
        install(by_name[matches[0]])
    subprocess.run([str(a.pkg_add), '-S', '-I', '-P', str(root), '-K', str(a.prefix / 'pkgdb'),
                    str(archive)], env=env, check=True)
    installed.add(package)
def options():
    return command(a.pkg_info, '-K', db, '-Q', 'PKG_OPTIONS', plain_name).split()
def files():
    return command(a.pkg_info, '-K', db, '-qL', plain_name).splitlines()
install(a.plain)
assert 'style' not in options()
assert not any('libtextstyle' in f for f in files())
assert not any(n.startswith(('glib2-', 'libcroco-')) for n in installed), installed
install(a.glib)
install(a.libcroco)
subprocess.run([str(a.pkg_add), '-S', '-I', '-P', str(root), '-K', str(a.prefix / 'pkgdb'),
                '-U', str(a.full)], env=env, check=True)
assert 'style' in options()
assert any('libtextstyle.0.dylib' in f for f in files())
# An installed full composition is the fast path: it is not downgraded.
assert 'style' in options() and (root / str(a.prefix).lstrip('/') / 'lib/libtextstyle.0.dylib').is_file()
for package in (plain_name, name(a.glib), name(a.libcroco)):
    subprocess.run([str(a.pkg_admin), '-P', str(root), '-K', str(db), 'check', package], env=env, check=True)
print('PASS: offline payload plain -> GLib/libcroco -> same-identity full -U; scripts deferred')
