#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), Perl MAKE_ENV argument regression.
"""Run the real MAKE_ENV clause with an accepted bmake and shell tuple.

Use the SDK owned-process interface. No Perl or install-name tool is executed.
The selected shell checks the environment that bmake actually supplies.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

NAME = 'EMBERBSD_DARWIN_INSTALL_NAME_TOOL'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def clause(text):
    start = text.index('.if ${OPSYS} == "Darwin" && defined(' + NAME + ')\n')
    end = text.index('.endif\n', start) + len('.endif\n')
    return text[start:end]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('makefile', 'shell', 'new-work'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--make-arg', action='append', required=True)
    args = cli.parse_args()
    command, work = args.make_arg, args.new_work
    require(args.makefile.is_absolute() and args.makefile.is_file(), 'Select the exported Makefile')
    require(args.shell.is_absolute() and args.shell.is_file() and os.access(args.shell, os.X_OK),
            'Select an executable shell')
    require(not any(c.isspace() for c in str(args.shell)), 'The .SHELL path must be one word')
    require(len(command) == 5 and command[1] == '-m' and
            command[3] == 'SHELL=' + str(args.shell) and command[4].startswith('MAKECONF=') and
            all(os.path.isabs(path) for path in (command[0], command[2], command[4][9:])),
            'Use the complete accepted bmake tuple')
    require(work.is_absolute() and work.resolve() == work and not os.path.lexists(work),
            'Use new absolute work')
    production = clause(args.makefile.read_text())
    work.mkdir(mode=0o700)
    empty_path = work / 'empty-path'; empty_path.mkdir()
    selected = work / 'selected tools' / 'install name tool'
    selected.parent.mkdir(); selected.write_bytes(b'fixture is never executed\n')
    link = work / 'selected link'; link.symlink_to(selected)
    check = work / 'check-env.sh'
    check.write_text('if [ "$TEST_EXPECT_DEFINED" = yes ]; then\n'
                     '    [ "${' + NAME + '+x}" = x ] || exit 81\n'
                     '    [ "$' + NAME + '" = "$TEST_EXPECT_VALUE" ] || exit 82\n'
                     'else\n'
                     '    [ "${' + NAME + '+x}" != x ] || exit 83\n'
                     'fi\necho PASS\n')
    cases = [('darwin-unset', 'Darwin', None), ('darwin-empty', 'Darwin', ''),
             ('darwin-space', 'Darwin', str(selected)), ('darwin-symlink', 'Darwin', str(link)),
             ('netbsd-unset', 'NetBSD', None), ('netbsd-empty', 'NetBSD', ''),
             ('netbsd-selected', 'NetBSD', str(selected))]
    records = []
    for name, platform, value in cases:
        fixture = work / (name + '.mk')
        # Keep inputs in the makefile. Command-line variables may be exported by
        # bmake itself, which would conceal a missing MAKE_ENV assignment.
        require(value is None or not any(c in value for c in ('\n', '\r', '#')),
                'Fixture paths must fit one literal Makefile assignment')
        assignment = '' if value is None else NAME + '= ' + value.replace('$', '$$') + '\n'
        fixture.write_text('.SHELL: name=sh path=' + str(args.shell) +
            ' hasErrCtl=no check="set -e" ignore="set +e" echoFlag=v errFlag=e\n'
            'OPSYS= ' + platform + '\n' + assignment + production +
            'CHECKER= ' + str(check).replace('$', '$$') + '\n'
            '.PHONY: check\ncheck:\n\t@${MAKE_ENV} ${SHELL:Q} ${CHECKER:Q}\n')
        argv = [*command, '-r', '-f', str(fixture), 'check']
        defined = platform == 'Darwin' and value is not None
        env = dict(PATH=str(empty_path), LC_ALL='C', TZ='UTC', TMPDIR=str(work),
                   TEST_EXPECT_DEFINED='yes' if defined else 'no',
                   TEST_EXPECT_VALUE=value if defined else '')
        result = subprocess.run(argv, cwd=work, env=env, capture_output=True, timeout=30)
        (work / (name + '.stdout')).write_bytes(result.stdout)
        (work / (name + '.stderr')).write_bytes(result.stderr)
        records.append(dict(case=name, argv=argv, env=env, actual_exit=result.returncode,
            fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
            stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
            stderr_sha256=hashlib.sha256(result.stderr).hexdigest()))
        (work / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
        require(result.returncode == 0 and result.stderr == b'' and result.stdout == b'PASS\n',
                name + ': MAKE_ENV did not preserve the expected defined state and exact value')
    print(json.dumps(dict(status='PASS', actual_make_env_cases=len(records),
        scope='Actual bmake and selected shell; no Perl or install-name execution')))


if __name__ == '__main__':
    main()
