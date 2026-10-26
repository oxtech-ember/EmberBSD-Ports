#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check Ninja's declared od tool and the actual binary-to-header generator."""
import argparse
import os
from pathlib import Path
import re
import subprocess


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('bmake', 'pkgsrc', 'makeconf', 'shell', 'od', 'sed', 'printf', 'source', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    args = cli.parse_args()
    args.work.mkdir()
    keys = ('PKG_FAIL_REASON', 'USE_TOOLS', 'TOOLS_CREATE', 'TOOLS_PATH.od')
    result = subprocess.run([str(args.bmake), '-C', str(args.pkgsrc / 'devel/ninja-build'),
        'MAKECONF=' + str(args.makeconf), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        'WRKOBJDIR=' + str(args.work / 'objects'),
        'TOOLS_PLATFORM.od=' + str(args.od),
        *[word for key in keys for word in ('-V', key + '=${' + key + '}')]],
        capture_output=True, text=True, check=True)
    (args.work / 'metadata.log').write_text(result.stdout + result.stderr)
    assert not result.stderr, result.stderr
    row = dict(line.split('=', 1) for line in result.stdout.splitlines())
    assert not row['PKG_FAIL_REASON'], row
    assert 'od' in row['USE_TOOLS'].split(), row
    assert 'od' in row['TOOLS_CREATE'].split(), row
    assert row['TOOLS_PATH.od'] == str(args.od), row
    script = args.source / 'src/inline.sh'
    assert script.is_file()
    for tool in (args.od, args.sed, args.printf, args.shell):
        assert tool.is_absolute() and tool.is_file() and os.access(tool, os.X_OK), tool
    payload = b'inline\n\x00\xff\\"\tend\n'
    for label, with_od in (('missing-od', False), ('selected', True)):
        tools = args.work / label
        tools.mkdir()
        (tools / 'sed').symlink_to(args.sed)
        (tools / 'printf').symlink_to(args.printf)
        if with_od:
            (tools / 'od').symlink_to(row['TOOLS_PATH.od'])
        result = subprocess.run([str(args.shell), str(script), 'inline_fixture'],
            input=payload, env={'PATH': str(tools), 'LC_ALL': 'C'}, capture_output=True)
        (args.work / (label + '.stdout')).write_bytes(result.stdout)
        (args.work / (label + '.stderr')).write_bytes(result.stderr)
        if not with_od:
            assert result.returncode != 0 and not result.stdout and b'od' in result.stderr, result
        else:
            assert result.returncode == 0 and not result.stderr, result
            text = result.stdout.decode('ascii')
            assert text.startswith('const char inline_fixture[] = \n') and text.endswith(';'), text
            encoded = bytes(int(value, 16) for value in re.findall(r'\\x([0-9a-f]{2})', text))
            assert encoded == payload, (encoded, payload)
    print('PASS: actual recipe declares selected od; unchanged inline.sh fails without it and preserves all input bytes with it')


if __name__ == '__main__':
    main()
