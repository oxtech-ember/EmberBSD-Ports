#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check the configured NetBSD seed runtime policy without compilation."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess


TEMPLATE = b'*link_libgcc:\n%D\n'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def link_command(trace):
    commands = []
    for line in trace.decode('utf-8', 'strict').splitlines():
        try:
            words = shlex.split(line)
        except ValueError:
            continue
        if words and Path(words[0]).name == 'collect2':
            commands.append(words)
    require(len(commands) == 1, 'expected the normal collect2 link command')
    return commands[0]


def check(prefix, template, work, forbidden):
    prefix = prefix.resolve(strict=True)
    require(template.read_bytes() == TEMPLATE, 'unexpected runtime policy bytes')
    require(work.is_dir() and not any(work.iterdir()), 'use a new empty work directory')
    specs = work / 'runtime.specs'
    specs.write_bytes(TEMPLATE)
    env = dict(PATH=str(prefix / 'bin'), LC_ALL='C', TZ='UTC', TMPDIR=str(work))
    records = []
    for driver, language in (('gcc', 'c'), ('g++', 'c++')):
        executable = prefix / 'bin' / driver
        command = [str(executable), '-B' + str(prefix) + '/', '-specs=' + str(specs),
                   '-static-libgcc']
        if language == 'c++':
            command.append('-static-libstdc++')
        output = work / (driver + '.output')
        baseline_query = [word for word in command if not word.startswith('-specs=')]
        baseline_query.extend(('-###', '-x', language, os.devnull, '-o', str(output)))
        baseline = subprocess.run(baseline_query, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=30, check=True)
        baseline_trace = work / (driver + '.baseline.trace')
        baseline_trace.write_bytes(baseline.stdout + baseline.stderr)
        baseline_link = link_command(baseline.stderr)
        require(any(word == '-rpath' and forbidden in baseline_link[index + 1]
                    for index, word in enumerate(baseline_link[:-1])),
                'input does not exhibit the retained configured runtime paths')
        query = [*command, '-###', '-x', language, os.devnull, '-o', str(output)]
        result = subprocess.run(query, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=30, check=True)
        trace = work / (driver + '.trace')
        trace.write_bytes(result.stdout + result.stderr)
        require(not output.exists(), 'a dry run unexpectedly created an output')
        words = link_command(result.stderr)
        require('-rpath' not in words and '-lgcc_s' not in words,
                'the seed still adds dynamic GCC runtime routes')
        require(not any(forbidden in word for word in words), 'historical runtime route remains')
        require('-lgcc' in words and '-lgcc_eh' in words, 'static GCC runtime selection changed')
        if language == 'c++':
            require('-lstdc++' in words and '-Bstatic' in words[:words.index('-lstdc++')],
                    'C++ did not select its static runtime')
        archives = {}
        for name in ('libgcc.a', 'libgcc_eh.a', 'crtbegin.o', 'crtend.o') + (
                ('libstdc++.a', 'libsupc++.a') if language == 'c++' else ()):
            answer = subprocess.check_output([*command, '-print-file-name=' + name],
                                             env=env, timeout=30).decode().strip()
            path = Path(answer).resolve(strict=True)
            require(path.is_relative_to(prefix), 'runtime query escaped the selected prefix: ' + answer)
            archives[name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        records.append(dict(driver=driver, argv=query, runtime=archives,
            baseline_trace=dict(path=str(baseline_trace), sha256=hashlib.sha256(baseline_trace.read_bytes()).hexdigest()),
            policy_trace=dict(path=str(trace), sha256=hashlib.sha256(trace.read_bytes()).hexdigest())))
    report = dict(status='PASS', scope='read-only-runtime-routes', compilation_performed=False,
                  external_as_ld_execution_observed=False,
                  template_sha256=hashlib.sha256(TEMPLATE).hexdigest(), drivers=records)
    (work / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: configured NetBSD seed runtime routes; no compilation or qualification')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', required=True, type=Path)
    parser.add_argument('--template', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'bootstrap/netbsd11-configured-base-seed.specs.in')
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--forbidden-runtime-root', required=True)
    args = parser.parse_args()
    check(args.prefix, args.template, args.work, args.forbidden_runtime_root)
