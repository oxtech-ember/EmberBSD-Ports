#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), Python extraction tool metadata regression.
"""Query actual pkgsrc metadata with an explicit bmake tuple and environment.

This verifies one Python extraction edge, not the complete bootstrap graph.
The SDK must separately validate the complete graph and producer source inputs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

KEYS = ('PKGNAME', 'EXTRACT_USING', 'TOOLS_PATH.bsdtar', '_EXTRACT_TAR',
        'TOOLS_DEPENDS.bsdtar', 'TOOL_DEPENDS', 'EXTRACT_OPTS', 'USE_TOOLS',
        'TOOLBASE', 'USE_CROSS_COMPILE')


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check(row, selected):
    require(row['PKGNAME'] == 'python315-3.15.1nb2', 'Require the revised Python recipe')
    require(row['EXTRACT_USING'] == 'bsdtar', 'The PAX provider was not selected')
    require(row['TOOLS_PATH.bsdtar'] == row['_EXTRACT_TAR'] == selected,
            'Extraction must use the explicitly expected native bsdtar path')
    require(selected == str(Path(row['TOOLBASE']) / 'bin/bsdtar'), 'Do not use an ambient host provider')
    require(any(word.startswith('bsdtar') and word.endswith(':../../archivers/bsdtar')
                for word in row['TOOL_DEPENDS'].split()), 'Require the native bsdtar tool dependency')
    require(row['TOOLS_DEPENDS.bsdtar'].endswith(':../../archivers/bsdtar'), 'Provider owner differs')
    require(any(word.split(':')[0] == 'bsdtar' for word in row['USE_TOOLS'].split()), 'bsdtar tool was omitted')
    options = shlex.split(row['EXTRACT_OPTS'])
    require(any(options[i:i + 2] == ['-t', selected] for i in range(len(options))),
            'The extractor command does not name the selected provider')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'env-json', 'new-work', 'expected-tar'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--make-arg', action='append', required=True)
    args = cli.parse_args()
    command, work = args.make_arg, args.new_work
    require(len(command) == 5 and command[1] == '-m' and command[3].startswith('SHELL=')
            and command[4].startswith('MAKECONF=') and all(os.path.isabs(path) for path in
                (command[0], command[2], command[3][6:], command[4][9:])), 'Use the complete accepted bmake tuple')
    require(args.pkgsrc.is_absolute() and (args.pkgsrc / 'lang/python315/Makefile').is_file(), 'Use the real export')
    require(args.expected_tar.is_absolute(), 'Bind the expected future native tool path')
    require(work.is_absolute() and work.resolve() == work and not os.path.lexists(work), 'Use new absolute work')
    environment = json.loads(args.env_json.read_text())
    require(isinstance(environment, dict) and all(isinstance(k, str) and isinstance(v, str)
            for k, v in environment.items()) and environment.get('LC_ALL') == 'C'
            and 'PATH' in environment, 'Supply the complete accepted environment')
    work.mkdir(mode=0o700)
    argv = [*command, '-C', str(args.pkgsrc / 'lang/python315'),
            'WRKOBJDIR=' + str(work / 'objects'), 'PACKAGES=' + str(work / 'packages'),
            '_PKGSRC_BARRIER=yes', *[word for key in KEYS for word in ('-V', key + '=${' + key + '}')]]
    result = subprocess.run(argv, cwd=work, env=environment, capture_output=True, timeout=60)
    (work / 'stdout').write_bytes(result.stdout); (work / 'stderr').write_bytes(result.stderr)
    (work / 'command.json').write_text(json.dumps(dict(argv=argv, env=environment, actual_exit=result.returncode,
        stdout_sha256=hashlib.sha256(result.stdout).hexdigest(), stderr_sha256=hashlib.sha256(result.stderr).hexdigest()), indent=2) + '\n')
    require(result.returncode == 0 and result.stderr == b'', 'Actual metadata query failed')
    lines = result.stdout.decode().splitlines()
    require(len(lines) == len(KEYS) and all(line.startswith(key + '=') for key, line in zip(KEYS, lines)),
            'Unexpected metadata framing')
    row = {key: line.removeprefix(key + '=') for key, line in zip(KEYS, lines)}
    (work / 'metadata.json').write_text(json.dumps(row, indent=2) + '\n')
    check(row, str(args.expected_tar))
    print(json.dumps(dict(status='PASS', scope='One actual extraction tool edge; no complete graph or build acceptance')))


if __name__ == '__main__':
    main()
