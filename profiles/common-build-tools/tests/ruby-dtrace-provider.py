#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Selected Ruby DTrace preprocessing.
"""Exercise the real Ruby platform post-wrapper recipe with selected inputs."""
import argparse
import os
from pathlib import Path
import subprocess


def require(value, message):
    if not value:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform-mk', type=Path, required=True)
    parser.add_argument('--make', type=Path, required=True)
    parser.add_argument('--shell', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    echo = args.shell.parent / 'gecho'
    chmod = args.shell.parent / 'gchmod'
    require(all(path.is_absolute() and path.is_file() for path in
                (args.platform_mk, args.make, args.shell, echo, chmod)),
            'Use actual absolute prefix inputs')
    require(args.work.is_absolute() and not os.path.lexists(args.work),
            'Use a fresh absolute work directory')
    source = args.platform_mk.read_text()
    start = source.index('CONFIGURE_ENV.SunOS+=\tOBJCOPY=:')
    end = source.index('\n#\n# bmake doesn', start)
    recipe = source[start:end].rstrip()
    selected_dtrace = args.work / 'selected-provider' / 'dtrace'
    selected_cc = args.work / 'selected-prefix' / 'bin' / 'clang'
    wrapper_dir = args.work / 'wrapper-bin'
    wrapper_dir.mkdir(parents=True)
    (args.work / 'selected-provider').mkdir()
    (args.work / 'selected-prefix/bin').mkdir(parents=True)
    record = args.work / 'dtrace-argv'
    selected_dtrace.write_text(
        f'#!{args.shell}\nfor arg do print -r -- "$arg"; done > {record}\n')
    selected_dtrace.chmod(0o755)
    makefile = args.work / 'Makefile'

    def makefile_text(opsys='Darwin', provider=selected_dtrace, override=None):
        variables = ('.SHELL: name=sh path=' + str(args.shell) +
                     ' hasErrCtl=no check="set -e" ignore="set +e" echoFlag=v errFlag=e\n' +
                     f'OPSYS= {opsys}\nEMBERBSD_DARWIN_BOOTSTRAP= yes\n')
        if provider is not None:
            variables += f'TOOLS_PLATFORM.dtrace= {provider}\n'
        variables += f'PKG_CC= {selected_cc}\n'
        if override is not None:
            variables += f'DTRACE= {override}\n'
        return (variables + f'SH= {args.shell}\nWRAPPER_BINDIR= {wrapper_dir}\n' +
                f'RUN= @\nECHO= {echo}\nCHMOD= {chmod}\n' + recipe + '\n')

    env = {'PATH': str(args.work / 'empty-bin'), 'LC_ALL': 'C', 'TZ': 'UTC'}
    (args.work / 'empty-bin').mkdir()

    def run(target='post-wrapper', filename=makefile):
        return subprocess.run([str(args.make), '-r', '-f', str(filename), target],
                              cwd=args.work, env=env, capture_output=True, text=True)

    makefile.write_text(makefile_text())
    result = run()
    require(result.returncode == 0 and result.stderr == '',
            'The real post-wrapper rule failed: ' + result.stderr.strip())
    wrapper = wrapper_dir / 'dtrace'
    require(wrapper.is_file(), 'The selected DTrace provider did not create its wrapper')
    result = subprocess.run([str(wrapper), 'source file.d', '-n', 'probe name'],
                            cwd=args.work, env=env, capture_output=True, text=True)
    require(result.returncode == 0 and result.stderr == '',
            'The generated wrapper did not execute the selected provider')
    argv = record.read_text().splitlines()
    require(argv == [f'-xcpppath={selected_cc}', 'source file.d', '-n', 'probe name'],
            'The selected preprocessor or spaced DTrace arguments were not preserved: ' +
            repr(argv))
    text = wrapper.read_text()
    require('/usr/sbin/dtrace' not in text and
            'PATH=/bin:/usr/bin:/sbin:/usr/sbin' not in text,
            'Ruby DTrace wrapper contains an implicit system fallback')
    wrapper.unlink()

    missing = args.work / 'missing-provider.mk'
    missing.write_text(makefile_text(provider=None))
    result = subprocess.run([str(args.make), '-r', '-f', str(missing),
                             '-V', 'PKG_FAIL_REASON'], cwd=args.work,
                            env=env, capture_output=True, text=True)
    require(result.returncode == 0 and result.stderr == '' and
            'Select the declared DTrace provider' in result.stdout,
            'A missing bootstrap DTrace provider was not refused')
    require(not wrapper.exists(), 'A missing provider created a system DTrace fallback')

    mismatch = args.work / 'mismatched-provider.mk'
    mismatch.write_text(makefile_text(override=args.work / 'other-dtrace'))
    result = subprocess.run([str(args.make), '-r', '-f', str(mismatch),
                             '-V', 'PKG_FAIL_REASON'], cwd=args.work,
                            env=env, capture_output=True, text=True)
    require(result.returncode == 0 and result.stderr == '' and
            'DTRACE must match the selected Darwin provider' in result.stdout,
            'A DTRACE override bypassed the selected bootstrap provider')
    require(not wrapper.exists(), 'A mismatched provider created a wrapper')

    other = args.work / 'other-platform.mk'
    other.write_text(makefile_text(opsys='NetBSD'))
    result = run(filename=other)
    require(result.returncode == 0 and result.stderr == '',
            'The non-Darwin post-wrapper rule failed')
    legacy = wrapper.read_text()
    require('PATH=/bin:/usr/bin:/sbin:/usr/sbin' in legacy and
            '/usr/sbin/dtrace' in legacy,
            'The existing non-Darwin DTrace behavior was removed')
    print('PASS: selected, absent, mismatched, and non-Darwin Ruby DTrace paths')


if __name__ == '__main__':
    main()
