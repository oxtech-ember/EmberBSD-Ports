#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Tool composition and target script paths.
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 5:
    sys.exit('Use GCC_PREFIX OS_TOOLDIR EXPORTED_PKGSRC MAKECONF NEW_WORK')
compiler, os_tools, pkgsrc, makeconf, work = args
work = Path(work).absolute()
work.mkdir()
helper = Path(__file__).resolve().parents[1] / 'cross/prepare-tools.py'
bmake = os.environ.get('BMAKE', 'bmake')


def run(label, command, accept=True):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True)
    (work / (label + '.log')).write_text(result.stdout + result.stderr)
    assert (result.returncode == 0) == accept, label + ': ' + result.stdout + result.stderr
    return result.stdout + result.stderr


command = [sys.executable, '-B', helper, '--sdk-source', sdk, compiler, os_tools, work / 'tools']
run('compose', command)
assert run('triplet', [work / 'tools/bin/aarch64--netbsd-gcc', '-dumpmachine']).strip() == 'aarch64--netbsd'
assert run('version', [work / 'tools/bin/aarch64--netbsd-gcc', '-dumpfullversion']).strip() == '16.2.0'
assert 'Output already exists' in run('existing', command, False)
(work / 'missing-os-tools').mkdir()
assert 'Missing cross tool or NetBSD host install' in run('missing', [sys.executable, '-B', helper, '--sdk-source', sdk, compiler, work / 'missing-os-tools', work / 'rejected'], False)
assert not (work / 'rejected').exists()
base = [bmake, '-C', pkgsrc + '/devel/m4', 'MAKECONF=' + makeconf]
result = run('info-present', base + ['show-vars', 'VARNAMES=PKG_FAIL_REASON INSTALL_INFO TOOLS_SCRIPT.install-info DEPENDS']).splitlines()
assert result[:3] == ['', '/usr/bin/install-info', 'exit 0'] and not any('pkg_install-info-' in line for line in result)
(work / 'empty-sysroot').mkdir()
assert 'install-info:run not supported in cross-compilation' in run('info-missing', base + ['EMBERBSD_CROSS_SYSROOT=' + str(work / 'empty-sysroot'), '-v', 'PKG_FAIL_REASON'])
assert 'gm4:run not supported in cross-compilation' in run('other-runtime-tool', base + ['USE_TOOLS=sh pwd gm4:run', '-v', 'PKG_FAIL_REASON'])
print('PASS: GCC16 tool composition, existing/missing refusals and target install-info routing')
