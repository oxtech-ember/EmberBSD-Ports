#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check native Ninja bootstrap budget forwarding without compiling Ninja."""
import argparse
import ast
from contextlib import redirect_stderr, redirect_stdout
import io
import os
from optparse import OptionParser
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import patch


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'pkgsrc', 'bmake', 'makeconf', 'od', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    args = cli.parse_args()
    args.work.mkdir()
    source = (args.source / 'configure.py').read_text()
    tree = ast.parse(source)
    platform = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Platform')
    platform_code = ast.get_source_segment(source, platform)
    parser_code = source[source.index('parser = OptionParser()'):source.index('platform = Platform(options.platform)')]
    rebuild = tree.body[-1]
    assert isinstance(rebuild, ast.If) and ast.unparse(rebuild.test) == 'options.bootstrap'
    rebuild_code = ast.get_source_segment(source, rebuild)

    def execute(argv, *, code=rebuild_code, failure=False):
        namespace = dict(OptionParser=OptionParser, os=os, sys=sys, Optional=Optional, List=List)
        output = io.StringIO()
        with patch.object(sys, 'argv', ['configure.py', *argv]), redirect_stdout(output), redirect_stderr(output):
            exec(platform_code, namespace)
            exec(parser_code, namespace)
            namespace['platform'] = namespace['Platform'](namespace['options'].platform or 'darwin')
            calls, renames = [], []
            def child(command):
                calls.append(command)
                if failure:
                    raise subprocess.CalledProcessError(37, command)
            namespace['subprocess'] = SimpleNamespace(check_call=child)
            namespace['os'] = SimpleNamespace(path=SimpleNamespace(exists=lambda p: False),
                rename=lambda old, new: renames.append((old, new)))
            exec(code, namespace)
        return calls, renames

    cases = [(['--bootstrap'], ['./ninja']),
             (['--bootstrap', '--bootstrap-jobs=18'], ['./ninja', '-j', '18']),
             (['--bootstrap', '--bootstrap-jobs=1', '--verbose'], ['./ninja', '-j', '1', '-v']),
             (['--bootstrap', '--platform=mingw', '--bootstrap-jobs=2'], ['ninja.bootstrap.exe', '-j', '2']),
             (['--bootstrap', '--platform=aix', '--bootstrap-jobs=3'], ['./ninja.bootstrap', '-j', '3'])]
    for argv, expected in cases:
        calls, renames = execute(argv)
        assert calls == [expected], (argv, calls)
        if '--platform=mingw' in argv:
            assert renames == [('ninja.exe', 'ninja.bootstrap.exe')], renames
    assert execute(['--bootstrap-jobs=18'])[0] == []
    for value in ('0', '-1', 'invalid'):
        try:
            execute(['--bootstrap', '--bootstrap-jobs=' + value])
        except SystemExit as error:
            assert error.code == 2, error
        else:
            raise AssertionError('invalid job count accepted: ' + value)
    try:
        execute(['--bootstrap', '--bootstrap-jobs=18'], failure=True)
    except subprocess.CalledProcessError as error:
        assert error.returncode == 37
    else:
        raise AssertionError('child failure was swallowed')
    omitted = "    if options.bootstrap_jobs is not None:\n        rebuild_args.extend(['-j', str(options.bootstrap_jobs)])\n\n"
    assert omitted in rebuild_code
    assert execute(['--bootstrap', '--bootstrap-jobs=18'], code=rebuild_code.replace(omitted, ''))[0] == [['./ninja']]

    for label, selected, expected in [('parallel', ['MAKE_JOBS=18'], 18),
                                     ('serialized', ['MAKE_JOBS=18', 'MAKE_JOBS_SAFE=no'], 1)]:
        command = [str(args.bmake), '-C', str(args.pkgsrc / 'devel/ninja-build'),
            'MAKECONF=' + str(args.makeconf), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
            'WRKOBJDIR=' + str(args.work / 'objects'),
            'TOOLS_PLATFORM.od=' + str(args.od), *selected, '-n', 'do-build']
        result = subprocess.run(command, capture_output=True, text=True)
        (args.work / (label + '.log')).write_text(result.stdout + result.stderr)
        result.check_returncode()
        assert not result.stderr, result.stderr
        assert './configure.py --bootstrap --bootstrap-jobs=' + str(expected) in result.stdout, result.stdout
    print('PASS: actual parser/child argv preserves default, forwards selected jobs and failures; native recipe forwards 18 or serialized1')


if __name__ == '__main__':
    main()
