#!/usr/bin/env python3
"""Check that Qt reads the selected macOS SDK without xcrun in PATH."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cmake', required=True, help='absolute Ports CMake executable')
    parser.add_argument('--helpers', required=True,
                        help='cmake/QtPublicAppleHelpers.cmake from the patched work source')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        sdk = work / 'MacOSX.sdk'
        sdk.mkdir()
        (sdk / 'SDKSettings.json').write_text(json.dumps({'Version': '15.0'}))
        empty = work / 'empty-path'
        empty.mkdir()
        script = work / 'probe.cmake'
        script.write_text(
            'set(APPLE TRUE)\n'
            'set(CMAKE_OSX_SYSROOT "' + str(sdk) + '")\n'
            'set(QT_NO_XCODE_MIN_VERSION_CHECK ON)\n'
            'include("' + str(Path(args.helpers).resolve()) + '")\n'
            '_qt_internal_get_apple_sdk_path(path)\n'
            '_qt_internal_get_apple_sdk_version(version)\n'
            '_qt_internal_get_xcode_version_raw(xcode)\n'
            'message(STATUS "probe:${path}|${version}|${xcode}")\n')
        result = subprocess.run([args.cmake, '-P', str(script)], capture_output=True, text=True,
                                env={'PATH': str(empty), 'HOME': str(work), 'LC_ALL': 'C'})
        expected = 'probe:' + str(sdk) + '|15.0|'
        output = result.stdout + result.stderr
        if result.returncode != 0 or expected not in output:
            print('FAIL: Qt does not use the selected SDK metadata: ' + ' '.join(output.split())[-300:])
            return 1
    print('PASS: Qt uses the selected SDK path and SDKSettings.json version')
    return 0


if __name__ == '__main__':
    sys.exit(main())
