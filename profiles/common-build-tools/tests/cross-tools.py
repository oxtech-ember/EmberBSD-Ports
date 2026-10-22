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
source_sysroot = Path(run('target-sysroot', base + ['show-vars', 'VARNAMES=CROSS_DESTDIR']).strip())
required_runtime = (
    'usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/crtbeginS.o',
    'usr/pkg/gcc16/lib/libstdc++.so.7',
    'usr/pkg/gcc16/include/c++/aarch64--netbsd/bits/c++config.h',
)

def info_sysroot(name, utility=None):
    target = work / name
    for relative in required_runtime:
        source = source_sysroot / relative
        if not source.is_file():
            raise SystemExit('Missing runtime fixture input: ' + str(source))
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source)
    if utility is not None:
        # The profile selects the base path by sysroot file presence only.
        destination = target / utility
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text('metadata fixture only\n')
    return target

query = 'show-vars'
variables = 'VARNAMES=PKG_FAIL_REASON INSTALL_INFO TOOLS_SCRIPT.install-info TOOLS_PATH.install-info DEPENDS'
base_tool = info_sysroot('sysroot-base-install-info', 'usr/bin/install-info')
result = run('info-base-provider', base + ['EMBERBSD_CROSS_SYSROOT=' + str(base_tool), query, variables]).splitlines()
assert 'install-info:run not supported in cross-compilation' not in result[0], result
assert result[1:4] == ['/usr/bin/install-info', 'exit 0', '/usr/bin/install-info'], result
assert not any('pkg_install-info-' in line for line in result[4:]), result

package_tool = info_sysroot('sysroot-pkg-install-info')
result = run('info-package-provider', base + ['EMBERBSD_CROSS_SYSROOT=' + str(package_tool), query, variables]).splitlines()
assert 'install-info:run not supported in cross-compilation' not in result[0], result
assert result[1:4] == ['/usr/pkg/bin/pkg_install-info', 'exit 0', '/usr/pkg/bin/pkg_install-info'], result
assert any('pkg_install-info-' in line and ':../../pkgtools/pkg_install-info' in line
           for line in result[4:]), result

missing_tool = info_sysroot('sysroot-missing-install-info')
assert 'install-info:run not supported in cross-compilation' in run(
    'info-no-provider', base + ['EMBERBSD_CROSS_SYSROOT=' + str(missing_tool),
    '_TOOLS_USE_PKGSRC.install-info=no', 'TOOLS_PLATFORM.install-info=',
    query, 'VARNAMES=PKG_FAIL_REASON'])

# gzip is an actual pkgsrc consumer of INFO_FILES. Keep the index and route
# its package lifecycle command to the selected target provider.
info_variables = (
    'VARNAMES=PKG_FAIL_REASON INFO_FILES GNU_CONFIGURE_INFODIR PKGINFODIR INSTALL_INFO '
    'TOOLS_SCRIPT.install-info TOOLS_PATH.install-info DEPENDS'
)
info_result = run('info-files-enabled', [bmake, '-C', pkgsrc + '/archivers/gzip',
    'MAKECONF=' + makeconf, 'show-vars', info_variables]).splitlines()
assert 'install-info:run not supported in cross-compilation' not in info_result[0], info_result
if (source_sysroot / 'usr/bin/install-info').is_file():
    expected_info_tool = '/usr/bin/install-info'
    assert not any('pkg_install-info-' in line for line in info_result[7:]), info_result
elif (source_sysroot / 'usr/pkg/bin/pkg_install-info').is_file():
    expected_info_tool = '/usr/pkg/bin/pkg_install-info'
    assert any('pkg_install-info-' in line and ':../../pkgtools/pkg_install-info' in line
               for line in info_result[7:]), info_result
else:
    raise SystemExit('The target sysroot has no accepted install-info provider')
assert info_result[1] == 'yes' and info_result[2] == '/usr/pkg/' + info_result[3], info_result
assert info_result[4:7] == [expected_info_tool, 'exit 0', expected_info_tool], info_result
assert 'gm4:run not supported in cross-compilation' in run('other-runtime-tool', base + ['USE_TOOLS=sh pwd gm4:run', '-v', 'PKG_FAIL_REASON'])
gts_base = [bmake, '-C', pkgsrc + '/graphics/gts', 'MAKECONF=' + makeconf]
gts_result = run('gts-libtool-tag', gts_base + [query, 'VARNAMES=PKG_FAIL_REASON PKGREVISION']).splitlines()
assert len(gts_result) == 2 and not gts_result[0].strip() and gts_result[1].strip() == '9', gts_result
print('PASS: GCC16 tools, gzip INFO_FILES, target install-info, GTS Libtool tag and cross-tool refusal')
