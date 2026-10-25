#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that boost-jam passes a toolset the b2 engine script supports."""
import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
# PKGSRC_COMPILER, OPSYS, extra lines and the expected b2 toolset of consumers.
CASES = (('darwin-gcc', 'gcc', 'Darwin', '', 'darwin'),
         ('darwin-pkgsrc-gcc', 'gcc', 'Darwin', 'GCCBASE= /fixture/gcc\n', 'gcc'),
         ('netbsd-gcc', 'gcc', 'NetBSD', '', 'gcc'),
         ('darwin-clang', 'clang', 'Darwin', '', 'clang'),
         ('sunos-sunpro', 'sunpro', 'SunOS', '', 'sunpro'))


def engine_toolsets(script):
    # The script prints the toolsets it supports in its usage text.
    text = script.read_text(encoding='utf-8')
    found = re.search(r'Toolsets supported by this script are:\n(.*?)\n\n', text, re.S)
    assert found, 'No toolset list in ' + str(script)
    names = set(re.findall(r'[a-z][a-z0-9-]*', found.group(1)))
    assert {'gcc', 'clang'} <= names and 'darwin' not in names, sorted(names)
    return names | {'cxx'}


def recipe_lines(source):
    # Use every assignment that reads BOOST_TOOLSET and the real do-build target.
    lines = source.splitlines(keepends=True)
    keep = [line for line in lines if re.match(r'[A-Z_]+[+?:]?=', line) and 'BOOST_TOOLSET' in line]
    start = lines.index('do-build:\n')
    end = start + 1
    while end < len(lines) and lines[end].startswith('\t'):
        end += 1
    return ''.join(keep) + ''.join(lines[start:end])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'bmake', 'shell', 'engine-script', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    args = cli.parse_args()
    for tool in (args.bmake, args.shell, args.engine_script):
        assert tool.is_absolute() and tool.is_file(), 'Use explicit absolute paths'
    supported = engine_toolsets(args.engine_script)
    toolset_mk = (args.pkgsrc / 'devel/boost-build/toolset.mk').resolve(strict=True)
    recipe = recipe_lines((args.pkgsrc / 'devel/boost-jam/Makefile').read_text(encoding='utf-8'))
    work = args.work.resolve()
    work.mkdir()
    (work / 'empty-path').mkdir()
    records = []
    for label, compiler, opsys, extra, consumer in CASES:
        fixture = work / (label + '.mk')
        fixture.write_text('PKGSRC_COMPILER= ' + compiler + '\nOPSYS= ' + opsys + '\n' + extra +
            'SETENV= env\nMAKE_ENV=\nSH= sh\nWRKSRC= /fixture/src\nCXXFLAGS= -O2\n' +
            '.include "' + str(toolset_mk) + '"\n.PHONY: do-build\n' + recipe, encoding='utf-8')
        results = {}
        for target, mode in (('do-build', ['-n', 'do-build']), ('show', ['-V', 'BOOST_TOOLSET'])):
            argv = [str(args.bmake), '-r', '-f', str(fixture), 'SHELL=' + str(args.shell)] + mode
            run = subprocess.run(argv, cwd=work, capture_output=True, timeout=30,
                env={'PATH': str(work / 'empty-path'), 'LC_ALL': 'C'})
            (work / (label + '.' + target + '.stdout')).write_bytes(run.stdout)
            (work / (label + '.' + target + '.stderr')).write_bytes(run.stderr)
            records.append({'case': label, 'argv': argv, 'status': run.returncode})
            (work / 'commands.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
            assert run.returncode == 0 and not run.stderr, (label, target, run.stderr)
            results[target] = run.stdout.decode()
        assert results['show'].strip() == consumer, (label, results['show'])
        words = shlex.split(re.sub(r'\\\n[ \t]*', ' ', results['do-build']))
        engine = words[words.index('./build.sh') + 1]
        if engine not in supported:
            raise SystemExit('FAIL: ' + label + ' runs build.sh ' + engine +
                             ', which the engine script does not support')
    print('PASS: %d toolset cases; the engine script gets a supported toolset and '
          'consumers keep theirs' % len(CASES))


if __name__ == '__main__':
    main()
