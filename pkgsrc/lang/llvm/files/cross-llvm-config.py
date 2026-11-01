#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build-host llvm-config from installed LLVM packages.
"""Compile upstream llvm-config from installed target and native LLVM metadata.

Usage: cross-llvm-config.py CONFIG WORK PKGSRC SYSROOT
"""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
from llvm_config_validation import validate_llvm_config

VERSION = '23.1.4'


def fail(message):
    print('cross-llvm-config: ' + message, file=sys.stderr)
    return 1


def reports_version(config):
    if not os.access(config, os.X_OK):
        return False
    result = subprocess.run([config, '--version'], capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() == VERSION


def main(arguments):
    if arguments[:1] == ['--validate']:
        if len(arguments) != 3:
            return fail('usage: cross-llvm-config.py --validate CONFIG SYSROOT')
        try:
            validate_llvm_config(arguments[1], arguments[2])
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            return fail(str(error))
        return 0
    if len(arguments) != 4:
        return fail(__doc__.splitlines()[2])
    config, work, pkgsrc, sysroot = arguments
    config, work, pkgsrc, sysroot = Path(config), Path(work), Path(pkgsrc), Path(sysroot)
    expected = work / 'helper/bin/llvm-config'
    if config != expected:
        try:
            validate_llvm_config(config, sysroot)
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            return fail(str(error))
        print('cross-llvm-config: use ' + str(config))
        return 0
    host = os.environ.get('EMBERBSD_HOST_PREFIX', '')
    if not host.startswith('/'):
        return fail('EMBERBSD_HOST_PREFIX must name the selected native Ports prefix')
    work.parent.mkdir(parents=True, exist_ok=True)
    with open(work.parent / (work.name + '.lock'), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        producer = pkgsrc / 'lang/llvm/files/build-installed-llvm-config.py'
        command = [sys.executable, '-B', str(producer), str(config), str(work), str(sysroot), host]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as error:
            return fail('installed-package producer failed with status ' + str(error.returncode))
    if not reports_version(str(config)):
        return fail(str(config) + ' does not report LLVM ' + VERSION)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
