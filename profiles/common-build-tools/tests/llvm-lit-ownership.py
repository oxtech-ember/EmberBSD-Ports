#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real pkgtools private provider transition fixture.
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 2:
    sys.exit('Use HOST_PKGTOOLS_DIRECTORY NEW_WORK')
tools, work = Path(args[0]).absolute(), Path(args[1]).absolute()
work.mkdir()
root = work / 'root'
root.mkdir()


def run(expected, command):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != 'PKG_PATH'})
    with (work / 'commands.log').open('a') as log:
        log.write(repr(command) + '\n' + result.stdout + result.stderr + '\nstatus=' + str(result.returncode) + '\n')
    assert (result.returncode == 0) == expected, result.stdout + result.stderr
    return result.stdout


(work / 'comment').write_text('LLVM Python ownership fixture')
(work / 'description').write_text('Test data; this package is not a compiler.')
(work / 'build-info').write_text('OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=aarch64\nOBJECT_FMT=ELF\n')
old, new = 'py314-llvm-lit-23.1.3', 'py315-llvm-lit-23.1.3nb1'
consumer, replacement = 'llvm-python-consumer-1.0', 'llvm-python-consumer-1.0nb1'
packages = {}
for name, dependency, conflict in [(old, None, False), (new, None, True), (consumer, old, False), (replacement, new, False)]:
    stage = work / name
    (stage / 'bin').mkdir(parents=True)
    relative = 'bin/compiler-fixture' if dependency else 'bin/lit'
    (stage / relative).write_text('compiler payload retained' if dependency else name)
    plist = '@cwd /usr/pkg\n@name ' + name + '\n' + ('@pkgdep ' + dependency + '\n' if dependency else '') + ('@pkgcfl py[0-9]*-llvm-lit-[0-9]*\n' if conflict else '') + relative + '\n'
    (stage / 'plist').write_text(plist)
    packages[name] = work / (name + '.tgz')
    run(True, [tools / 'pkg_create', '-p', stage, '-I', '/usr/pkg', '-f', stage / 'plist', '-c', work / 'comment', '-d', work / 'description', '-B', work / 'build-info', packages[name]])


def add(name, expected=True):
    run(expected, [tools / 'pkg_add', '-U', '-I', '-P', root, '-K', '/usr/pkg/pkgdb', '-m', 'NetBSD/aarch64 11.0', packages[name]])


def delete(name, force=False, expected=True):
    run(expected, [tools / 'pkg_delete', '-D', '-P', root, '-K', '/usr/pkg/pkgdb', *(['-f'] if force else []), name])


add(old)
add(consumer)
add(new, False)
assert (root / 'usr/pkg/bin/lit').read_text() == old
delete(old, expected=False)
assert (root / 'usr/pkg/bin/compiler-fixture').read_text() == 'compiler payload retained'
delete(old, force=True)
add(new)
add(replacement)
assert (root / 'usr/pkg/bin/lit').read_text() == new
assert (root / 'usr/pkg/pkgdb' / new / '+REQUIRED_BY').read_text().splitlines() == [replacement]
delete(new, force=True)
add(old)
add(consumer)
assert (root / 'usr/pkg/bin/compiler-fixture').read_text() == 'compiler payload retained'
assert (root / 'usr/pkg/bin/lit').read_text() == old
assert (root / 'usr/pkg/pkgdb' / old / '+REQUIRED_BY').read_text().splitlines() == [consumer]
print('PASS: private pkgtools conflicts, guarded removal, provider replacement, retained consumer and rollback')
