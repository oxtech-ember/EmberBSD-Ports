#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 The EmberBSD Project contributors.
# Developed with AI assistance.
"""Exercise actual profile filename ownership and IO allocation failure paths."""
import argparse
from pathlib import Path
import shlex
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--profile-file', type=Path, help='override only the source under test')
    parser.add_argument('--runtime-archive', type=Path, required=True,
                        help='matching native common profile archive for unchanged helpers')
    parser.add_argument('--cflags', default='')
    parser.add_argument('--expect-failure', action='store_true',
                        help='baseline causal control; requires AddressSanitizer and UBSan in cflags')
    args = parser.parse_args()
    flags = shlex.split(args.cflags)
    sanitizers = ','.join(flag for flag in flags if flag.startswith('-fsanitize='))
    if args.expect_failure and not all(name in sanitizers for name in ('address', 'undefined')):
        parser.error('--expect-failure needs -fsanitize=address,undefined')
    root = args.source.resolve()
    profile = root / 'compiler-rt/lib/profile'
    source = args.profile_file.resolve() if args.profile_file else profile / 'InstrProfilingFile.c'
    fixture = Path(__file__).with_name('profile-memory-fixture.c')
    common = [args.cc, *flags, '-UNDEBUG', '-Wall', '-Wextra', '-Werror',
              '-I'+str(profile), '-I'+str(root/'compiler-rt/include')]
    cases = ('quiet', 'same', 'different', 'environment', 'borrowed', 'default',
             'invalid', 'io-normal', 'io-buffer-failure', 'io-writer-failure',
             'io-foreign-buffer')
    with tempfile.TemporaryDirectory(prefix='profile-memory-') as temporary:
        work = Path(temporary)
        obj, binary = work/'profile.o', work/'fixture'
        subprocess.run([*common, '-Dcalloc=fixture_calloc', '-Dstrdup=fixture_strdup',
                        '-Dfree=fixture_free', '-c', str(source), '-o', str(obj)], check=True)
        subprocess.run([*common, str(fixture), str(obj), str(args.runtime_archive.resolve()),
                        '-o', str(binary)], check=True)
        for case in cases:
            result = subprocess.run([str(binary), case], cwd=work,
                                    text=True, capture_output=True, timeout=15)
            failure = args.expect_failure and case in (
                'different', 'environment', 'default', 'invalid',
                'io-writer-failure', 'io-foreign-buffer')
            if failure:
                diagnostic = ('heap-use-after-free' if not case.startswith('io-')
                              else 'member access within null pointer')
                if not result.returncode or diagnostic not in result.stderr:
                    raise SystemExit(result.stdout+result.stderr+'missing baseline failure: '+case)
            else:
                if result.returncode:
                    raise SystemExit(result.stdout+result.stderr+'failed: '+case)
                if 'ownership and' not in result.stdout:
                    raise SystemExit('missing completed assertions: '+case)
                if case not in ('quiet', 'same') and not case.startswith('io-'):
                    old = {'environment': 'environment.profraw',
                           'borrowed': 'default.profraw'}.get(case, 'old.profraw')
                    new = 'default.profraw' if case in ('default', 'invalid') else 'new.profraw'
                    if f'Override old profile path "{old}"' not in result.stderr or \
                       f'to "{new}" via runtime API.' not in result.stderr:
                        raise SystemExit('wrong verbose filename: '+result.stderr)
            print(case, 'expected baseline failure' if failure else 'PASS', flush=True)


if __name__ == '__main__':
    main()
