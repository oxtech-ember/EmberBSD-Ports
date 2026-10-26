#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 The EmberBSD Project contributors.
# Developed with AI assistance.
"""Inject GCDA allocation failures in the actual current and libc ABI source."""
import argparse
from pathlib import Path
import shlex
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', required=True)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--gcda', type=Path)
    parser.add_argument('--cflags', default='')
    parser.add_argument('--expect-failure', action='store_true', help='causal check of an unfixed baseline only')
    args = parser.parse_args()
    profile = args.source.resolve() / 'compiler-rt/lib/profile'
    source = args.gcda.resolve() if args.gcda else profile / 'GCDAProfiling.c'
    fixture = Path(__file__).with_name('gcda-allocation-fixture.c')
    with tempfile.TemporaryDirectory(prefix='gcda-allocations-') as temporary:
        work = Path(temporary)
        for legacy in (False, True):
            mode = '-DCOMPILER_RT_LIBC_LEGACY_GCOV' if legacy else '-DTEST_CURRENT_GCOV_ABI'
            name = 'legacy' if legacy else 'current'
            common = [args.cc, *shlex.split(args.cflags), '-Wall', '-Werror',
                '-DCOMPILER_RT_HAS_FCNTL_LCK=1', '-DCOMPILER_RT_HAS_UNAME=1',
                '-I'+str(profile), '-I'+str(args.source.resolve()/'compiler-rt/include')]
            utility, obj, binary = (work/(name+suffix) for suffix in ('-util.o','-gcda.o','-test'))
            subprocess.run([*common, '-c', str(profile/'InstrProfilingUtil.c'), '-o', str(utility)], check=True)
            subprocess.run([*common, '-Wextra', mode, '-Dmalloc=fixture_malloc',
                '-Drealloc=fixture_realloc', '-Dstrdup=fixture_strdup', '-Dfdopen=fixture_fdopen',
                '-c', str(source), '-o', str(obj)], check=True)
            subprocess.run([*common, '-Wextra', mode, str(fixture), str(obj), str(utility), '-o', str(binary)], check=True)
            for failure in ('callback','filename','prefixed-filename','initial-buffer','growing-buffer','merge'):
                result = subprocess.run([str(binary), str(work/(name+'-'+failure+'.gcda')), failure],
                    text=True, capture_output=True)
                print(name, failure, 'exit='+str(result.returncode), flush=True)
                if args.expect_failure:
                    if result.returncode == 0:raise SystemExit('baseline unexpectedly survived: '+failure)
                elif result.returncode or not any(message in result.stderr.lower() for message in ('out of memory', 'cannot allocate')):
                    raise SystemExit(result.stdout+result.stderr+'allocation recovery failed: '+failure)
            # Model the size_t allocation bound of a supported 32-bit host
            # inside the unchanged production source, before malloc and loops.
            limits = work / 'size-limit.h'
            limits.write_text('#include <stdint.h>\n#undef SIZE_MAX\n#define SIZE_MAX UINT32_MAX\n')
            subprocess.run([*common, '-Wextra', mode, '-Dfdopen=fixture_fdopen', '-include', str(limits),
                '-c', str(source), '-o', str(obj)], check=True)
            subprocess.run([*common, '-Wextra', mode, str(fixture), str(obj), str(utility), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary), str(work/(name+'-overflow.gcda')), 'counter-size-overflow'],
                text=True, capture_output=True)
            print(name, 'counter-size-overflow', 'exit='+str(result.returncode), flush=True)
            if args.expect_failure:
                if result.returncode == 0:raise SystemExit('baseline unexpectedly survived counter size overflow')
            elif result.returncode or 'counter array too large' not in result.stderr:
                raise SystemExit(result.stdout+result.stderr+'counter size bound failed')


if __name__ == '__main__':
    main()
