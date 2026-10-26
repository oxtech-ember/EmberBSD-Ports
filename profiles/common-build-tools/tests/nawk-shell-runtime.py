#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check real awk commands, both pipe directions, and ordinary language cases."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--awk', required=True, type=Path)
    cli.add_argument('--work', required=True, type=Path)
    args = cli.parse_args()
    if not args.awk.is_absolute() or not args.work.is_absolute():
        cli.error('Select absolute executable and new work paths')
    args.work.mkdir()
    env = dict(os.environ, LC_ALL='C')
    for name in ('KSH_VERSION', 'ENV', 'BASH_ENV'):
        env.pop(name, None)
    cases = [
        ('system-shell', '''BEGIN { exit system("case \\\"$KSH_VERSION\\\" in *MIRBSD*) exit 0;; *) exit 41;; esac") }''', '', ''),
        ('read-shell', '''BEGIN { c="printf '%s\\\\n' \\\"$KSH_VERSION\\\""; if ((c | getline v) != 1 || v !~ /MIRBSD/) exit 42; if (close(c)) exit 43 }''', '', ''),
        ('write-shell', '''BEGIN { c="read v; case \\\"$KSH_VERSION:$v\\\" in *MIRBSD*:pipe-output) printf 'selected\\\\n' >pipe-result;; *) exit 44;; esac"; print "pipe-output" | c; if (close(c)) exit 45 }''', '', ''),
        ('system-exit', 'BEGIN { print system("exit 37") }', '', '37\n'),
        ('system-exec-error', 'BEGIN { print system("exec /nonexistent/nawk-runtime-command 2>/dev/null") }', '', '127\n'),
        # Canonical run.c reports a signal as 256 + WTERMSIG, not shell status.
        ('system-signal', 'BEGIN { print system("kill -KILL $$") }', '', '265\n'),
        ('read-pipe-eof', '''BEGIN { c="printf 'value\\\\n'"; print (c | getline v),v; print (c | getline v); print close(c) }''', '', '1 value\n0\n0\n'),
        ('pipe-exec-error', 'BEGIN { c="exec /nonexistent/nawk-runtime-command 2>/dev/null"; print (c | getline v); print close(c) }', '', '0\n0\n'),
        ('reopen-pipe', '''BEGIN { for(i=0;i<3;i++){ c="printf 'again\\\\n'"; if ((c | getline v)!=1 || v!="again" || close(c)) exit 46 } }''', '', ''),
        ('fields', '{ sum += $2 } END { print NR,sum }', 'a 2\nb 3\n', '2 5\n'),
        ('split-regex', 'BEGIN { n=split("red:green:blue",a,/:/); print n,a[2]; s="aa11bb"; gsub(/[0-9]+/,"-",s); print s }', '', '3 green\naa-bb\n'),
        ('functions-arrays', 'function twice(x) { return x*2 } BEGIN { a["x"]=7; print twice(a["x"]), ("x" in a); delete a["x"]; print ("x" in a) }', '', '14 1\n0\n'),
    ]
    records = []
    for name, source, stdin, expected in cases:
        result = subprocess.run([str(args.awk), source], input=stdin.encode(), env=env,
                                cwd=args.work, capture_output=True, timeout=15)
        records.append(dict(name=name, actual_exit=result.returncode,
                            stdout=result.stdout.decode(errors='replace'),
                            stderr=result.stderr.decode(errors='replace')))
        (args.work / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
        if result.returncode != 0 or result.stdout != expected.encode() or result.stderr:
            raise AssertionError(name + ': unexpected exit or output; inspect results.json')
        if name == 'write-shell' and (args.work / 'pipe-result').read_bytes() != b'selected\n':
            raise AssertionError('write pipe did not use the selected mksh')
    print('PASS: 12 real awk shell, pipe, error, and language cases')


if __name__ == '__main__':
    main()
