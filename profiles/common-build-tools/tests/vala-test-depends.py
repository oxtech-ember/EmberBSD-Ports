#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
'''Check the Vala D-Bus test prerequisite with real BSD make dependency rules.'''
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('pkgsrc', type=Path)
    cli.add_argument('new_work', type=Path)
    cli.add_argument('--bmake', default='bmake')
    args = cli.parse_args()
    source = args.pkgsrc.resolve(strict=True)
    work = args.new_work
    require(sys.version_info >= (3, 15), 'Use Python 3.15 or newer.')
    require(work.is_absolute() and work.resolve() == work and not work.exists()
            and not work.is_symlink(), 'Use a new absolute canonical work path.')
    require(not work.is_relative_to(source), 'Keep work outside the input export.')
    work.mkdir(mode=0o700)
    (work / 'tmp').mkdir()
    env = dict(os.environ, LC_ALL='C', MAKECONF='/dev/null',
               TMPDIR=str(work / 'tmp'), TMP=str(work / 'tmp'), TEMP=str(work / 'tmp'))
    for key in ('MAKEFLAGS', 'MFLAGS', 'MAKELEVEL'):
        env.pop(key, None)
    commands = []

    def run(label, argv, cwd):
        result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env,
                                capture_output=True, timeout=30)
        (work / (label + '.stdout')).write_bytes(result.stdout)
        (work / (label + '.stderr')).write_bytes(result.stderr)
        commands.append(dict(label=label, argv=list(map(str, argv)),
                             cwd=str(cwd), status=result.returncode))
        (work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require(result.returncode == 0 and not result.stderr,
                'Unexpected BSD make/patch result: ' + label)
        return result.stdout.decode()

    line = 'TEST_DEPENDS+=\tdbus>=1.16.2:../../sysutils/dbus\n'
    recipe = (source / 'lang/vala/Makefile').read_text()
    require(recipe.count(line) <= 1, 'Duplicate D-Bus test declaration.')
    before = recipe.replace(line + '\n', '') if line in recipe else recipe
    require(line not in before, 'Cannot recover the declaration-free baseline.')
    delta = Path(__file__).resolve().parents[1] / 'patches/pkgsrc-vala-dbus-fd-exhaustion.patch'
    patch = delta.read_text()
    start = patch.index('--- a/lang/vala/Makefile\n')
    end = patch.index('--- a/lang/vala/distinfo\n', start)
    (work / 'makefile.patch').write_text(patch[start:end])
    variants = {}
    for name in ('before', 'after', 'tool-fault'):
        tree = work / name
        directory = tree / 'lang/vala'
        directory.mkdir(parents=True)
        (directory / 'Makefile').write_text(before)
        if name != 'before':
            output = run('patch-' + name, ['patch', '-f', '-F', '0', '-p1', '-d', tree,
                                         '-i', work / 'makefile.patch'], work)
            require('offset' not in output and 'fuzz' not in output,
                    'The production recipe delta must apply at its exact location.')
        updated = (directory / 'Makefile').read_text()
        if name == 'tool-fault':
            updated = updated.replace(line, line.replace('TEST_DEPENDS', 'TOOL_DEPENDS'))
        # Evaluate actual recipe assignments. Do not load compiler/platform probes or a DB.
        assignments = updated.split('.include ', 1)[0]
        fixture = assignments + f'''
PKGNAME=vala-fixture
PKGSRC_SETENV=/usr/bin/env
PKGSRCDIR={source}
WRKDIR={directory}/objects
WRKSRC={directory}
BUILD_DIRS=.
_COOKIE.test={directory}/test-cookie
_CLEANING=no
PKG_FAIL_REASON=
RUN=@
AWK=awk
SED=sed
SH=/bin/sh
CAT=cat
TEST=test
PWD_CMD=pwd -P
PKG_ADMIN=/usr/bin/false
_HOST_PKG_BEST_EXISTS=printf 'fixture-host-tool\\n'
_PKG_BEST_EXISTS=printf 'fixture-${{ROLE}}\\n'
HOST_PKG_INFO=printf 'fixture-format\\n'
PKG_INFO=printf 'fixture-format\\n'
OBJECT_FMT=fixture-format
NATIVE_OBJECT_FMT=fixture-format
STEP_MSG=echo
TRUE=true
FALSE=false
ERROR_MSG=echo
WARNING_MSG=echo
FAIL_MSG=false
.include "{source}/mk/pkgformat/pkg/depends.mk"
.include "{source}/mk/build/test.mk"
ordinary:
\t@${{_LIST_DEPENDS_CMD}}
test-list:
\t@${{_LIST_DEPENDS_CMD.test}}
route:
\t@type=test; pattern='dbus>=1.16.2'; dir=.; ${{_DEPENDS_INSTALL_CMD}}
'''
        (directory / 'check.mk').write_text(fixture)
        # reduce-depends uses real source directories, without package lookups.
        (tree / 'textproc').symlink_to(source / 'textproc', target_is_directory=True)
        (tree / 'sysutils').symlink_to(source / 'sysutils', target_is_directory=True)
        variants[name] = directory
    rows = {}
    keys = ['DISTNAME', 'PKGREVISION', 'TEST_TARGET', 'TEST_DEPENDS', 'TOOL_DEPENDS',
            'BUILD_DEPENDS', 'DEPENDS', '_TEST_TARGETS']
    for name, directory in variants.items():
        for role, cross in [('native', 'no'), ('cross', 'yes')]:
            label = name + '-' + role
            argv = [args.bmake, '-r', '-f', 'check.mk', 'ROLE=' + role,
                    'USE_CROSS_COMPILE=' + cross, 'TOOLS_USE_CROSS_COMPILE=' + cross]
            values = run(label + '-metadata', argv + [a for key in keys for a in ['-V', '${' + key + '}']], directory).splitlines()
            require(len(values) == len(keys), 'Unexpected metadata row count.')
            row = dict(zip(keys, values))
            row['ordinary'] = run(label + '-ordinary', argv + ['ordinary'], directory)
            row['tests'] = run(label + '-tests', argv + ['test-list'], directory)
            row['route'] = run(label + '-route', argv + ['route'], directory)
            valid = (row['TEST_DEPENDS'].split() == [line.split('+=\t', 1)[1].strip()]
                     and 'dbus' not in row['ordinary']
                     and row['tests'].split() == ['test', 'dbus>=1.16.2', '../../sysutils/dbus'])
            require(valid == (name == 'after'), 'The test must detect missing or wrongly scoped prerequisites.')
            require(row['DISTNAME'] == 'vala-0.56.19' and row['PKGREVISION'] == '2'
                    and row['TEST_TARGET'] == 'check' and 'test-depends' in row['_TEST_TARGETS'].split(),
                    'Preserve source version, upstream check and the normal test prerequisite gate.')
            require('found fixture-' + role in row['route'], 'The standard test dependency must use the selected package context.')
            rows[label] = row
    files = ['lang/vala/Makefile', 'mk/pkgformat/pkg/depends.mk', 'mk/build/test.mk',
             'mk/pkgformat/pkg/list-dependencies', 'mk/pkgformat/pkg/reduce-depends.awk']
    result = dict(status='PASS', cases=len(rows), rows=rows,
                  inputs={name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in files},
                  patch_sha256=hashlib.sha256(delta.read_bytes()).hexdigest(),
                  limits='Source/BSD make dependency fixtures only. No live package DB, compiler, install or Vala test execution.')
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', cases=len(rows))))


if __name__ == '__main__':
    main()
