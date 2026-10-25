#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check Darwin ID command selection with explicit bmake dry runs."""
import argparse
import json
import re
import shlex
import sys
from pathlib import Path

sys.dont_write_bytecode = True
RECIPES = ('databases/sqlite3', 'databases/sqlite3-tcl', 'sysutils/coreutils')


def id_command(source):
    # Use the production command, including its continuation lines.
    lines = source.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines)
              if line.startswith('\t') and 'install_name_tool' in line and ' -id' in line]
    assert len(starts) == 1, 'Expected one Darwin ID command'
    start = end = starts[0]
    while lines[end].rstrip().endswith('\\'):
        end += 1
    assert '.if ${OPSYS} == "Darwin"\n' in lines[:start]
    assert lines[end + 1] == '.endif\n'
    return ''.join(lines[start:end + 1])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'bmake', 'shell', 'sdk-source', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    args = cli.parse_args()
    for tool in (args.bmake, args.shell):
        assert tool.is_absolute() and tool.is_file(), 'Use explicit tool paths'
    sdk = args.sdk_source.resolve(strict=True)
    sys.path.insert(0, str(sdk / 'src'))
    from emberbsd_sdk import API_VERSION
    from emberbsd_sdk.stream import capture_streamed
    assert API_VERSION == 1
    work = args.work.resolve()
    work.mkdir()
    empty_path = work / 'empty-path'
    empty_path.mkdir()
    selected = str(work / 'selected tools' / 'install-name-tool')
    cases = (('default', None, 'install_name_tool'),
             ('selected-space', selected, selected),
             ('invalid-defined', 'missing-selected-tool', 'missing-selected-tool'),
             ('empty-defined', '', None))
    records = []
    for number, recipe in enumerate(RECIPES):
        command = id_command((args.pkgsrc / recipe / 'Makefile').read_text())
        defaults = ('PREFIX= /fixture/prefix\nDESTDIR= /fixture/dest\n'
                    'TCL_BASEVER= 9.1\nPKGVERSION_NOREV= 3.54.1\n')
        for label, value, first in (*cases, ('other-os', selected, None)):
            name = str(number) + '-' + label
            fixture = work / (name + '.mk')
            fixture.write_text(defaults + 'OPSYS= ' + ('NetBSD' if label == 'other-os' else 'Darwin') + '\n' +
                ('' if value is None else 'EMBERBSD_DARWIN_INSTALL_NAME_TOOL= ' + value + '\n') +
                '.PHONY: post-install\npost-install:\n.if ${OPSYS} == "Darwin"\n' + command + '.endif\n')
            argv = [str(args.bmake), '-r', '-f', str(fixture), '-n',
                    'SHELL=' + str(args.shell), 'post-install']
            result = capture_streamed(argv, cwd=str(work), timeout=30,
                env={'PATH': str(empty_path), 'LC_ALL': 'C'}, stdout_limit=65536)
            (work / (name + '.stdout')).write_bytes(result.value)
            (work / (name + '.stderr')).write_bytes(result.stderr)
            records.append({'recipe': recipe, 'case': label, 'argv': argv})
            (work / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
            words = shlex.split(re.sub(r'\\\n[ \t]*', ' ', result.value.decode()))
            if label == 'other-os':
                assert '-id' not in words and 'install_name_tool' not in result.value.decode(), (recipe, label, words)
                continue
            if first is not None:
                assert words[0] == first, (recipe, label, words)
                operands = words[1:]
            else:
                # An explicitly empty input must not select the ordinary tool.
                assert 'install_name_tool' not in words, (recipe, label, words)
                operands = words[1:] if words and words[0] == '' else words
            assert len(operands) == 3 and operands[0] == '-id', (recipe, label, words)
            assert operands[2] == '/fixture/dest' + operands[1], (recipe, label, words)
    print('PASS: 15 explicit bmake dry runs; no ID tool was executed')


if __name__ == '__main__':
    main()
