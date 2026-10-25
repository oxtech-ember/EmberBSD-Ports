#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), tests the complete pinned bsd.options.mk.
"""Check explicit xargs ECHO routing with selected tools and an empty PATH.

Use repeated --make-arg options for the accepted complete bmake tuple.
Only the unrelated prefs and obsolete-option includes are test doubles.
This probe does not build packages or qualify its supplied tools.
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


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--make-arg', action='append', required=True)
    for name in ('source', 'shell', 'xargs', 'awk', 'builtin-helper', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    a = cli.parse_args()
    work = a.work.absolute()
    require(not work.exists() and not work.is_symlink(), 'Work must be fresh.')
    for path in (a.source, a.shell, a.xargs, a.awk, a.builtin_helper):
        require(path.is_absolute() and path.is_file(), 'Use explicit selected input paths.')
    original = a.source.read_bytes()
    old = b'${XARGS} -n 1 |'
    fixed = b'${XARGS} -n 1 ${ECHO} |'
    require(original.count(fixed) == 2 and old not in original, 'Both source call sites must select ECHO.')
    work.mkdir()
    empty_path = work / 'empty-path'
    empty_path.mkdir()
    require(not any(empty_path.iterdir()), 'The test PATH must contain no external echo.')
    # Preserve the whole options implementation. Its two include interfaces
    # provide no host discovery or legacy defaults in this options-only test.
    results = []
    variants = {'fixed': original, 'old': original.replace(fixed, old),
                'missing-filter-command': original.replace(fixed, old, 1),
                'missing-selected-command': original[::-1].replace(fixed[::-1], old[::-1], 1)[::-1]}
    for variant, raw in variants.items():
        root = work / variant
        (root / 'defaults').mkdir(parents=True)
        (root / 'bsd.options.mk').write_bytes(raw)
        (root / 'bsd.prefs.mk').write_text('# Host selection is outside this options-only probe.\n')
        (root / 'defaults/obsolete.mk').write_text('# No legacy option aliases in this probe.\n')
        for label, options in (('nonempty', 'alpha beta'), ('empty', '')):
            mk = root / (label + '.mk')
            mk.write_text('OPSYS=Darwin\nPKGBASE=fixture\nPKG_OPTIONS_VAR=PKG_OPTIONS.fixture\n'
                + 'PKG_SUPPORTED_OPTIONS=' + options + '\nPKG_SUGGESTED_OPTIONS=' + options
                + '\nERROR_MSG=${ECHO}\n.include "bsd.options.mk"\n'
                + '.PHONY: fixture-wrap\nfixture-wrap:\n'
                + '\t@${ECHO} ${PKG_OPTIONS:Q} | ${_PKG_OPTIONS_WORDWRAP_FILTER}\n')
            for target in ('fixture-wrap', 'supported-options-message'):
                argv = [*a.make_arg, '-r', '-f', str(mk), 'SHELL=' + str(a.shell),
                    'ECHO=' + shlex.join([str(a.shell), str(a.builtin_helper), 'echo']),
                    'XARGS=' + str(a.xargs), 'AWK=' + str(a.awk), target]
                run = subprocess.run(argv, cwd=root, env=dict(PATH=str(empty_path), LC_ALL='C',
                    HOME=str(work), MAKEFLAGS='', MAKECONF='/dev/null'), capture_output=True, timeout=30)
                name = label + '-' + target
                (root / (name + '.stdout')).write_bytes(run.stdout)
                (root / (name + '.stderr')).write_bytes(run.stderr)
                if target == 'fixture-wrap':
                    output_ok = run.stdout == (b'\talpha beta\n' if options else b'')
                else:
                    output_ok = run.stdout.splitlines().count(b'\talpha beta') == 2 if options else run.stdout == b''
                passed = run.returncode == 0 and not run.stderr and output_ok
                results.append(dict(variant=variant, case=name, argv=argv, actual_exit=run.returncode,
                    stdout_sha256=hashlib.sha256(run.stdout).hexdigest(),
                    stderr_sha256=hashlib.sha256(run.stderr).hexdigest(), oracle_passed=passed))
                if variant == 'fixed':
                    require(passed, name + ' failed: ' + run.stderr.decode(errors='replace'))
        if variant != 'fixed':
            require(any(not row['oracle_passed'] for row in results if row['variant'] == variant),
                    variant + ' did not expose the missing command.')
    require(not any(empty_path.iterdir()), 'An executable appeared in the empty PATH.')
    (work / 'result.json').write_text(json.dumps(dict(status='PASS', source_sha256=hashlib.sha256(original).hexdigest(),
        selected_echo=[str(a.shell), str(a.builtin_helper), 'echo'], external_echo_available=False,
        cases=results, scope='Options output routing only. No package or provider qualification.'), indent=2) + '\n')
    print('PASS: empty and nonempty options use the complete selected ECHO command; both removal controls fail.')


if __name__ == '__main__':
    main()
