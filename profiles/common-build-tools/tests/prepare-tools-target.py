#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run the real prepare-tools.py with fake tools.
"""Check imports and amd64 tool composition without a real compiler."""
import ast
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 1:
    sys.exit('Use NEW_WORK')
work = Path(args[0]).absolute()
work.mkdir()
helper = Path(__file__).resolve().parents[1] / 'cross/prepare-tools.py'
ports = Path(__file__).resolve().parents[3]


def quarantine(path):
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and [t.id for t in node.targets if isinstance(t, ast.Name)] == ['PRODUCER_QUARANTINE']:
            return ast.literal_eval(node.value)
    raise AssertionError('No PRODUCER_QUARANTINE in ' + str(path))


# host.py resolves sdk_source to the LLVM module here; both copies must agree.
assert quarantine(ports / 'pkgsrc/lang/llvm/files/sdk_source.py') == \
    quarantine(ports / 'profiles/development-toolchain/runtime/recipe/files/sdk_source.py')
names = ('gcc', 'g++', 'cpp', 'gcc-ar', 'gcc-nm', 'gcc-ranlib', 'ar', 'as', 'elfedit', 'ld', 'nm', 'objcopy', 'objdump', 'ranlib', 'readelf', 'size', 'strings', 'strip')


def fake_prefix(path, triplet, machine):
    (path / 'bin').mkdir(parents=True)
    for name in names:
        tool = path / 'bin' / (triplet + '-' + name)
        tool.write_text('#!/bin/sh\ncase "$1" in -dumpmachine) echo %s;; -dumpfullversion) echo 16.2.0;; esac\n' % machine)
        tool.chmod(0o755)


def run(label, *command, accept=True):
    result = subprocess.run([sys.executable, '-B', str(helper), '--sdk-source', sdk] + [str(c) for c in command], capture_output=True, text=True)
    output = result.stdout + result.stderr
    (work / (label + '.log')).write_text(output)
    assert (result.returncode == 0) == accept, label + ': ' + output
    assert 'Traceback' not in output and 'ImportError' not in output, label + ': ' + output
    return output


fake_prefix(work / 'gcc-amd64', 'x86_64--netbsd', 'x86_64--netbsd')
fake_prefix(work / 'gcc-wrong', 'x86_64--netbsd', 'aarch64--netbsd')
(work / 'os-tools/bin').mkdir(parents=True)
install = work / 'os-tools/bin/x86_64--netbsd-install'
install.write_text('#!/bin/sh\nexit 0\n')
install.chmod(0o755)
assert 'Prepared GCC16 cross tools' in run('amd64', '--target', 'amd64', work / 'gcc-amd64', work / 'os-tools', work / 'tools')
for name in names:
    link = work / 'tools/bin' / ('x86_64--netbsd-' + name)
    assert link.is_symlink() and link.resolve() == (work / 'gcc-amd64/bin' / ('x86_64--netbsd-' + name)).resolve(), name
assert (work / 'tools/bin/x86_64--netbsd-install').resolve() == install.resolve()
for name in ('elfedit', 'size', 'strings'):
    link = work / 'tools/bin' / ('x86_64--netbsd-' + name)
    assert link.is_symlink() and link.resolve() == (work / 'gcc-amd64/bin' / ('x86_64--netbsd-' + name)).resolve(), name
# The kernel link runs ${SIZE}. A prefix that omits it must fail before output exists.
missing_size = work / 'gcc-missing-size'
fake_prefix(missing_size, 'x86_64--netbsd', 'x86_64--netbsd')
(missing_size / 'bin/x86_64--netbsd-size').unlink()
# The preflight must name size before it tries to run the compiler.
(missing_size / 'bin/x86_64--netbsd-gcc').write_text('#!/bin/sh\nexit 99\n')
(missing_size / 'bin/x86_64--netbsd-gcc').chmod(0o755)
missing = run('missing-size', '--target', 'amd64', missing_size, work / 'os-tools', work / 'rejected-size', accept=False)
assert 'Missing required external toolchain tools: size' in missing, missing
assert 'Required:' in missing and 'elfedit' in missing and 'strings' in missing, missing
assert not (work / 'rejected-size').exists()
assert 'Matching GCC16.2.0 target compiler required' in run('wrong-compiler', '--target', 'amd64', work / 'gcc-wrong', work / 'os-tools', work / 'rejected', accept=False)
assert not (work / 'rejected').exists()
assert 'Output already exists' in run('existing', '--target', 'amd64', work / 'gcc-amd64', work / 'os-tools', work / 'tools', accept=False)
print('PASS: prepare-tools.py imports, amd64 composition and target refusals')
