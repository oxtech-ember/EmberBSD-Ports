#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Actual Configure fragment regression.
"""Run only Perl's early shell/shebang and late option fragments with selected tools.

Use the SDK owned-process interface around this fixture. It does not configure
or compile Perl. Its only child interpreter is the explicit selected shell.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess


def require(value, message):
    if not value:
        raise AssertionError(message)


def fragments(configure, policy):
    """Read the real source; do not emulate the early tests or -D serializer."""
    start = configure.index("\nsh=''\n") + 1
    end = configure.index("targetsh=''\n", start) + len("targetsh=''\n")
    initialization = configure[start:end]
    start = configure.index(': Find the basic shell for Bourne shell scripts\n')
    end = configure.index('rm -f sharp today\n', start)
    early = configure[start:end]
    require(early.count('./sharp > today 2>/dev/null') == 2, 'Preserve both real shebang trials')
    require(early.count('\techo "#!$xcat" >sharp\n') == 1, 'Preserve the real shebang input')
    early = early.replace('\techo "#!$xcat" >sharp\n',
        '\ttest "$xcat" = "$PERL_BUILD_CAT" || exit 81\n\techo "#!$xcat" >sharp\n')
    start = configure.index('\t-D)\n')
    end = configure.index('\t-U)\n', start)
    define = configure[start:end]
    policy_line = next(line for line in policy.splitlines() if line.startswith("sh='"))
    require(policy_line == "sh='@TOOLS_SH@'", 'The real Policy.sh shell assignment changed')
    late = configure.index('. ./optdef.sh\n', configure.index('. Policy.sh\n'))
    require(late > configure.index('. Policy.sh\n'), 'The late command-line reapply is missing')
    return initialization, early, define, policy_line


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('configure', 'policy', 'shell', 'cat', 'utility_bin', 'new_work'):
        cli.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    args = cli.parse_args()
    require(all(path.is_absolute() and path.is_file() for path in
                (args.configure, args.policy, args.shell, args.cat)), 'Use explicit source files and selected binaries')
    require(args.utility_bin.is_absolute() and args.utility_bin.is_dir(), 'Select the accepted utility PATH')
    work = args.new_work
    require(work.is_absolute() and work.resolve() == work and not os.path.lexists(work), 'Use fresh work')
    configure, policy = args.configure.read_text(), args.policy.read_text()
    initial, early, define, policy_line = fragments(configure, policy)
    # Reject a missing selection before any legacy shell or shebang can run.
    # This is an assertion on the actual initialized state, not a replacement.
    initial += 'test "$sh" = "$PERL_BUILD_SHELL" || exit 80\n'
    work.mkdir(mode=0o700)
    records = []
    for name, runtime in [('native', str(args.shell)), ('cross', '/target/bin/sh')]:
        directory = work / name; directory.mkdir()
        script = directory / 'probe.sh'
        text = 'set -e\neunicefix=:\n_exe=\np_=:\npaths=\n' + initial + early
        text += '\ntest "$shsharp" = true\ntest "$sharpbang" = "#!"\n'
        text += 'test "$xcat" = "$PERL_BUILD_CAT"\n: >optdef.sh\n'
        # Arguments are supplied in upstream's already normalized -D form.
        # Run the actual upstream serializer for each of the two definitions.
        for value in ('sh=' + str(args.shell), 'targetsh=' + runtime):
            text += 'set -- -D ' + shlex.quote(value) + '\ncase "$1" in\n' + define + 'esac\n'
        text += '. ./optdef.sh\n'
        text += policy_line.replace('@TOOLS_SH@', '/policy-only/bin/sh') + '\n'
        text += 'test "$sh" = /policy-only/bin/sh\n. ./optdef.sh\n'
        text += 'test "$sh" = "$PERL_BUILD_SHELL"\n'
        text += 'test "$targetsh" = ' + shlex.quote(runtime) + '\n'
        text += 'echo "sh=$sh"\necho "targetsh=$targetsh"\necho "xcat=$xcat"\necho "sharpbang=$sharpbang"\n'
        script.write_text(text)
        environment = dict(PATH=str(args.utility_bin), LC_ALL='C', TZ='UTC', TMPDIR=str(directory),
                           PERL_BUILD_SHELL=str(args.shell), PERL_BUILD_CAT=str(args.cat))
        argv = [str(args.shell), str(script)]
        result = subprocess.run(argv, cwd=directory, env=environment, capture_output=True, timeout=60)
        (directory / 'stdout').write_bytes(result.stdout); (directory / 'stderr').write_bytes(result.stderr)
        record = dict(name=name, argv=argv, actual_exit=result.returncode,
            script_sha256=hashlib.sha256(script.read_bytes()).hexdigest())
        records.append(record)
        (work / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
        require(result.returncode == 0 and result.stderr == b'', 'Actual fragment failed: ' + name)
        require((directory / 'sharp').read_bytes() == ('#!' + str(args.cat) + '\n').encode(),
                'The real shebang trial did not use the selected cat binary')
        expected = f'sh={args.shell}\ntargetsh={runtime}\nxcat={args.cat}\nsharpbang=#!\n'.encode()
        require(result.stdout == expected, 'Early selection or late Policy precedence differs')
    print(json.dumps(dict(status='PASS', scope='Actual source fragment probes only; no Perl build or qualification', cases=len(records))))


if __name__ == '__main__':
    main()
