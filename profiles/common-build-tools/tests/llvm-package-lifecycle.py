#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Native pkgtools lifecycle on labelled fixtures.
import os
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk_source, args = load_sdk()
from emberbsd_sdk.inventory import snapshot_tree
if len(args) != 3:
    sys.exit('Use HOST_PREFIX SPLIT_FIXTURE NEW_OUTPUT')
host, fixture = map(os.path.realpath, args[:2])
work = Path(args[2]).absolute()
work.mkdir()


def run(label, tool, *arguments, expect=True):
    result = subprocess.run([host + '/sbin/' + tool, *map(str, arguments)], cwd=work, env={k: v for k, v in os.environ.items() if k != 'PKG_PATH'}, capture_output=True, text=True)
    (work / (label + '.log')).write_text(result.stdout + result.stderr)
    assert (result.returncode == 0) == expect, label + ': ' + result.stdout + result.stderr
    return result.stdout


version = run('pkgtools-version', 'pkg_create', '-V').strip()
assert re.fullmatch('[0-9]{8}', version)
(work / 'BUILD_INFO').write_text('OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=x86_64\nOBJECT_FMT=ELF\nLICENSE=2-clause-bsd\nPKGTOOLS_VERSION=' + version + '\nEMBERBSD_TEST_FIXTURE=yes\n')
(work / 'COMMENT').write_text('Labelled LLVM package partition fixture')
(work / 'DESCR').write_text('Synthetic text payloads. This is not a LLVM binary package.\n')
old, runtime, sdk = 'llvm-23.1.4', 'llvm-23.1.4nb1', 'llvm-devel-23.1.4nb2'
packages = {}
for name, stage, manifest, dependency in [(old, 'full-stage', 'full', None), (runtime, 'runtime-stage', 'runtime', None), (sdk, 'devel-stage', 'devel', runtime)]:
    prefix = Path(fixture, stage, 'usr/pkg')
    assert prefix.is_dir()
    files = Path(fixture, manifest, '.PLIST_nokeywords').read_text()
    text = '@name ' + name + '\n@cwd /usr/pkg\n'
    if dependency:
        text += '@pkgdep ' + dependency + '\n@pkgcfl llvm<23.1.4nb1\n'
    plist = work / (name + '.plist')
    plist.write_text(text + files)
    packages[name] = work / (name + '.tgz')
    run('create-' + name, 'pkg_create', '-l', '-U', '-p', prefix, '-I', '/usr/pkg', '-K', work / 'creation-pkgdb', '-B', work / 'BUILD_INFO', '-f', plist, '-c', work / 'COMMENT', '-d', work / 'DESCR', packages[name])
destination = work / 'root'
destination.mkdir()
database = destination / 'usr/pkg/pkgdb'
install = ['-K', '/usr/pkg/pkgdb', '-P', destination, '-m', 'NetBSD/x86_64 11.0']
remove = ['-K', '/usr/pkg/pkgdb', '-P', destination]


def snapshot(prefix, installed=False):
    return {k: row for k, row in snapshot_tree(str(prefix), exclude=['pkgdb'] if installed else []).items() if row['kind'] != 'directory'}


full_bytes = snapshot(Path(fixture, 'full-stage/usr/pkg'))
runtime_bytes = snapshot(Path(fixture, 'runtime-stage/usr/pkg'))


def verify(expected):
    assert snapshot(destination / 'usr/pkg', True) == expected


def registered(name):
    return run('registered-' + name, 'pkg_info', '-K', database, '-e', name).strip() == name


run('install-old-full', 'pkg_add', *install, packages[old])
verify(full_bytes)
assert (destination / 'usr/pkg/bin/llvm-config').is_file() and registered(old)
run('replace-with-runtime', 'pkg_add', '-u', *install, packages[runtime])
verify(runtime_bytes)
assert not (destination / 'usr/pkg/bin/llvm-config').exists() and (destination / 'usr/pkg/lib/libLLVM.so.23.1').is_file() and registered(runtime)
run('install-sdk', 'pkg_add', *install, packages[sdk])
verify(full_bytes)
assert registered(sdk) and (destination / 'usr/pkg/bin/llvm-tblgen').is_file()
assert runtime in run('sdk-dependencies', 'pkg_info', '-K', database, '-q', '-n', sdk).splitlines()
run('refuse-runtime-delete', 'pkg_delete', *remove, runtime, expect=False)
run('delete-sdk', 'pkg_delete', *remove, sdk)
verify(runtime_bytes)
run('delete-runtime', 'pkg_delete', *remove, runtime)
verify({})
assert not (destination / 'usr/pkg/lib/libLLVM.so.23.1').exists()
run('reinstall-runtime', 'pkg_add', *install, packages[runtime])
verify(runtime_bytes)
assert not (destination / 'usr/pkg/bin/llvm-config').exists()
run('delete-reinstalled-runtime', 'pkg_delete', *remove, runtime)
verify({})
print('PASS: private pkgtools replace full fixture with runtime, add/remove SDK, enforce dependencies and reinstall')
print('SCOPE: text fixtures; no target execution or shared package database changes')
