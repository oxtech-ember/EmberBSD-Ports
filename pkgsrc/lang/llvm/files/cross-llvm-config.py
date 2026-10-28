#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Make the build-host llvm-config of the target LLVM.
"""Use CONFIG, or make it in WORK from the lang/llvm build tree.

Usage: cross-llvm-config.py CONFIG WORK NATIVE_WORK PKGSRC SYSROOT ARCHIVE MAKE

The producers come from the export (EMBERBSD-LLVM-CONFIG). They check the
target build tree, the native build tree, the installed target LLVM headers
and the installed libLLVM. This script does not remove or replace any output.
"""
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
VERSION = '23.1.4'
SOURCE = 'llvm-project-' + VERSION + '.src'


def fail(message):
    print('cross-llvm-config: ' + message, file=sys.stderr)
    return 1


def reports_version(config):
    if not os.access(config, os.X_OK):
        return False
    result = subprocess.run([config, '--version'], capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() == VERSION


def target_build(make, pkgsrc):
    """Return the CMake build directory of lang/llvm for the same MAKECONF."""
    environment = {k: v for k, v in os.environ.items() if not k.startswith(('MAKE', '.MAKE'))}
    environment['MAKECONF'] = os.environ.get('MAKECONF', '')
    result = subprocess.run([make, '-V', '${WRKSRC}/${CMAKE_BUILD_DIR}'], cwd=pkgsrc / 'lang/llvm',
                            env=environment, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip().startswith('/'):
        raise SystemExit(fail('cannot evaluate the lang/llvm build directory: ' + result.stderr.strip()[:300]))
    return Path(result.stdout.strip())


def main(arguments):
    if len(arguments) != 7:
        return fail(__doc__.splitlines()[2])
    config, work, native, pkgsrc, sysroot, archive, make = arguments
    work, native, pkgsrc, sysroot = Path(work), Path(native), Path(pkgsrc), Path(sysroot)
    if reports_version(config):
        print('cross-llvm-config: use ' + config)
        return 0
    if Path(config) != work / 'sealed/bin/llvm-config':
        return fail('EMBERBSD_CROSS_LLVM_CONFIG=' + config + ' does not report LLVM ' + VERSION)
    if work.exists():
        return fail(str(work) + ' exists but has no working llvm-config; examine it, then remove it')
    tools = pkgsrc / 'EMBERBSD-LLVM-CONFIG'
    host = os.environ.get('EMBERBSD_HOST_PREFIX', '')
    if not host.startswith('/'):
        return fail('EMBERBSD_HOST_PREFIX must name the native Ports prefix')
    if not reports_version(str(native / 'native/bin/llvm-config')):
        if native.exists():
            return fail(str(native) + ' exists but has no working native llvm-config; examine it, then remove it')
        native.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, '-B', str(tools / 'profiles/common-build-tools/cross/build-llvm-native.py'),
                        archive, str(native), host + '/bin/cmake', host + '/bin/ninja'], check=True)
    target = target_build(make, pkgsrc)
    if not (target / 'CMakeCache.txt').is_file():
        return fail('no lang/llvm build tree at ' + str(target) + '; build lang/llvm and keep its WRKDIR')
    work.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-B', str(tools / 'scripts/build-llvm-config.py'),
                    '--sdk-source', os.environ.get('EMBERBSD_SDK_SOURCE', ''),
                    str(native / 'source' / SOURCE / 'llvm'), str(target), str(native / 'native'),
                    str(sysroot), str(sysroot / 'usr/pkg'), str(work)], check=True)
    if not reports_version(config):
        return fail(config + ' does not report LLVM ' + VERSION)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
