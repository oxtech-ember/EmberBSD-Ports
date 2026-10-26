#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise real GN Xcode generation. Do not compile or run Ninja targets."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile


def executable(value):
    path = Path(value)
    if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
        raise argparse.ArgumentTypeError('select an existing absolute executable')
    return str(path)


def check_case(gn, python, root, name, target_os, platform, sdk, family, error):
    case = root / name
    case.mkdir()
    (case / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n')
    declaration = '' if platform is None else (
        'declare_args() { target_xcode_platform = "iphoneos" }\n')
    (case / 'BUILDCONFIG.gn').write_text(
        declaration + 'set_default_toolchain("//:test")\n')
    (case / 'BUILD.gn').write_text('''toolchain("test") {
  tool("stamp") {
    command = "not-executed {{output}}"
  }
}
group("all") {}
''')
    args = f'target_os = "{target_os}"'
    if platform is not None:
        args += ' target_xcode_platform = ' + platform
    result = subprocess.run([
        gn, 'gen', 'out', '--root=' + str(case), '--ide=xcode',
        '--xcode-project=fixture', '--script-executable=' + python,
        '--args=' + args,
    ], cwd=case, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, timeout=60, check=False)
    print(f'{name}: exit={result.returncode}\n{result.stdout}', flush=True)
    project = case / 'out/fixture.xcodeproj'
    if error is not None:
        if result.returncode != 1 or error not in result.stdout:
            raise AssertionError(f'{name}: expected a normal GN error: {error}')
        if project.exists():
            raise AssertionError(f'{name}: invalid settings wrote an Xcode project')
        return
    if result.returncode:
        raise AssertionError(f'{name}: valid generation failed')
    pbx = (project / 'project.pbxproj').read_text()
    if not re.search(r'\bSDKROOT = ' + re.escape(sdk) + r';', pbx):
        raise AssertionError(f'{name}: wrong SDKROOT')
    families = re.findall(r'\bTARGETED_DEVICE_FAMILY = (.*?);', pbx)
    if family is None:
        if families:
            raise AssertionError(f'{name}: macOS acquired an iOS device family')
    elif not families or any(value.strip('"') != family for value in families):
        raise AssertionError(f'{name}: wrong TARGETED_DEVICE_FAMILY')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gn', required=True, type=executable)
    parser.add_argument('--python', required=True, type=executable)
    args = parser.parse_args()
    cases = [
        ('ios-default', 'ios', None, 'iphoneos', '1,2', None),
        ('ios-phone', 'ios', '"iphoneos"', 'iphoneos', '1,2', None),
        ('ios-tv', 'ios', '"tvos"', 'appletvos', '3', None),
        ('macos', 'mac', None, 'macosx', None, None),
        ('macos-unused-platform', 'mac', '7', 'macosx', None, None),
        ('ios-invalid-type', 'ios', '7', None, None,
         'target_xcode_platform value should be a string'),
        ('ios-unknown-platform', 'ios', '"invalid-platform"', None, None,
         'Unknown target_xcode_platform value'),
        ('ios-empty-platform', 'ios', '""', None, None,
         'Unknown target_xcode_platform value'),
    ]
    with tempfile.TemporaryDirectory(prefix='gn-xcode-errors-') as tmp:
        root = Path(tmp)
        for case in cases:
            check_case(args.gn, args.python, root, *case)
    print(f'gn-xcode-errors: PASS ({len(cases)} cases)')


if __name__ == '__main__':
    main()
