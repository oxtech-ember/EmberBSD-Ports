#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Native pkgtools lifecycle on labelled fixtures.
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

if len(sys.argv) != 4:
    raise SystemExit('Usage: qtbase-package-lifecycle.py HOST_PREFIX SPLIT_FIXTURE NEW_OUTPUT')
host, fixture = (Path(p).resolve(strict=True) for p in sys.argv[1:3])
work = Path(sys.argv[3])
if not work.is_absolute() or work.exists():
    raise SystemExit('new absolute output required')
work.mkdir()
tools = {n: host / 'sbin' / n for n in ('pkg_create', 'pkg_add', 'pkg_info', 'pkg_delete')}
env = dict(os.environ)
env.pop('PKG_PATH', None)
def run(label, tool, *args, expect=True):
    result = subprocess.run([str(tools[tool]), *map(str, args)], cwd=work, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (work / (label + '.log')).write_text(result.stdout)
    if (result.returncode == 0) != expect:
        raise SystemExit(label + ': ' + result.stdout)
    return result.stdout
version = run('pkgtools-version', 'pkg_create', '-V').strip()
if not re.fullmatch(r'[0-9]{8}', version):
    raise SystemExit('actual pkg_create version missing')
(work / 'BUILD_INFO').write_text('OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=x86_64\nOBJECT_FMT=ELF\nLICENSE=2-clause-bsd\nPKGTOOLS_VERSION=' + version + '\nEMBERBSD_TEST_FIXTURE=yes\n')
(work / 'COMMENT').write_text('Labelled Qtbase package partition fixture')
(work / 'DESCR').write_text('Synthetic text payloads for pkgtools contracts. This is not a Qt binary package.\n')
old, runtime, sdk = 'qt6-qtbase-6.12.0', 'qt6-qtbase-6.12.0nb8', 'qt6-qtbase-devel-6.12.0nb10'
packages = {}
for name, stage, manifest, dep in ((old,'normalized-full','full',None), (runtime,'runtime-stage','runtime',None), (sdk,'devel-stage','devel',runtime)):
    prefix = fixture / stage / 'usr/pkg'
    if not prefix.is_dir(): raise SystemExit('prepared source-contract fixture required')
    text = '@name ' + name + '\n@cwd /usr/pkg\n'
    if dep: text += '@pkgdep ' + dep + '\n@pkgcfl qt6-qtbase<6.12.0nb8\n'
    text += (fixture / manifest / '.PLIST_nokeywords').read_text()
    plist, archive = work / (name + '.plist'), work / (name + '.tgz')
    plist.write_text(text)
    run('create-' + name, 'pkg_create', '-l', '-U', '-p', prefix, '-I', '/usr/pkg', '-K', work / 'creation-pkgdb', '-B', work / 'BUILD_INFO', '-f', plist, '-c', work / 'COMMENT', '-d', work / 'DESCR', archive)
    packages[name] = archive
destination = work / 'root'
destination.mkdir()
database = destination / 'usr/pkg/pkgdb'
install = ['-K', '/usr/pkg/pkgdb', '-P', destination, '-m', 'NetBSD/x86_64 11.0']
remove = ['-K', '/usr/pkg/pkgdb', '-P', destination]
def snapshot(prefix, installed=False):
    files = {}
    for parent, dirs, names in os.walk(prefix, followlinks=False):
        parent = Path(parent)
        if installed and database == parent:
            dirs[:] = []
            continue
        for name in list(dirs):
            path = parent / name
            if path.is_symlink():
                files[str(path.relative_to(prefix))] = ('symlink', os.readlink(path))
                dirs.remove(name)
        for name in names:
            path = parent / name
            files[str(path.relative_to(prefix))] = ('symlink', os.readlink(path)) if path.is_symlink() else ('file', hashlib.sha256(path.read_bytes()).hexdigest())
    return files
full = snapshot(fixture / 'normalized-full/usr/pkg')
runtime_files = snapshot(fixture / 'runtime-stage/usr/pkg')
def verify(expected):
    if snapshot(destination / 'usr/pkg', installed=True) != expected: raise SystemExit('installed payload differs from the selected stage')
def registered(name): return run('registered-' + name, 'pkg_info', '-K', database, '-e', name).strip() == name
run('install-old-full','pkg_add',*install,packages[old]); verify(full)
if not (destination/'usr/pkg/qt6/bin/qmake').is_file() or not registered(old): raise SystemExit('old complete fixture absent')
run('replace-with-runtime','pkg_add','-u',*install,packages[runtime]); verify(runtime_files)
if (destination/'usr/pkg/qt6/bin/qmake').exists(): raise SystemExit('runtime replacement retained SDK files')
if not (destination/'usr/pkg/qt6/bin/qtpaths').is_file() or not registered(runtime): raise SystemExit('runtime replacement lost qtpaths or registration')
run('install-sdk','pkg_add',*install,packages[sdk]); verify(full)
if not registered(sdk): raise SystemExit('SDK package not registered')
if not (destination/'usr/pkg/qt6/libexec/moc').is_file(): raise SystemExit('SDK manifest omitted target tools')
if runtime not in run('sdk-dependencies','pkg_info','-K',database,'-q','-n',sdk).splitlines(): raise SystemExit('SDK exact runtime dependency not registered')
run('refuse-runtime-delete','pkg_delete',*remove,runtime,expect=False)
run('delete-sdk','pkg_delete',*remove,sdk); verify(runtime_files)
if not (destination/'usr/pkg/qt6/bin/qtpaths').is_file(): raise SystemExit('deleting SDK removed runtime qtpaths')
run('delete-runtime','pkg_delete',*remove,runtime); verify({})
if (destination/'usr/pkg/qt6/bin/qtpaths').exists(): raise SystemExit('runtime files survived deletion')
run('reinstall-runtime','pkg_add',*install,packages[runtime]); verify(runtime_files)
if (destination/'usr/pkg/qt6/bin/qmake').exists(): raise SystemExit('runtime reinstall restored development tools')
run('delete-reinstalled-runtime','pkg_delete',*remove,runtime); verify({})
print('PASS: normal pkg_create/pkg_add replace a full fixture with runtime, add/remove SDK, enforce dependencies and reinstall runtime')
print('SCOPE: private synthetic text fixtures; no compiled Qt, target execution or shared package database changes')
