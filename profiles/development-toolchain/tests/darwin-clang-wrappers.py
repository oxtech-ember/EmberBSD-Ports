#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Generate both real pkgsrc wrapper backends and run native Clang probes.

Use a current Ports export and an explicit Darwin bootstrap make tuple.
The libnbcompat recipe is read only; all generated wrappers and probes go
under --work. No package dependencies, installs or downloads are invoked.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shlex
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--make-arg', action='append', required=True,
                        help='Each argument of the complete bootstrap make command')
    parser.add_argument('--cwrappers-dir', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    assert args.work.is_absolute() and not args.work.exists(), 'Use a new absolute work directory'
    assert Path(args.make_arg[0]).is_absolute(), 'Select make explicitly'
    args.work.mkdir(parents=True)
    work = args.work.resolve()
    recipe = args.pkgsrc.resolve() / 'pkgtools/libnbcompat'
    reports = []
    for backend in ('traditional', 'cwrappers'):
        directory = work / backend
        directory.mkdir()
        (directory / '.barrier_cookie').touch()
        wrapper_dir = directory / ('.wrapper' if backend == 'traditional' else '.cwrapper')
        (wrapper_dir / 'bin').mkdir(parents=True)
        (wrapper_dir / ('tmp' if backend == 'traditional' else 'config')).mkdir()
        command = [*args.make_arg, 'USE_LANGUAGES=c c++', 'WRKDIR=' + str(directory),
                   'WRKSRC=' + str(directory), 'WRKLOG=' + str(directory / 'commands.log'),
                   '_USE_CWRAPPERS=' + ('no' if backend == 'traditional' else 'yes'),
                   'CWRAPPERS_SRC_DIR=' + str(args.cwrappers_dir.resolve())]
        env = dict(os.environ, LC_ALL='C')

        def make(*tail):
            result = subprocess.run([*command, *tail], cwd=recipe, env=env,
                                    text=True, capture_output=True, timeout=60)
            assert result.returncode == 0, result.stdout + result.stderr
            return result.stdout

        names = ['CC', 'CXX', 'CPP', 'AS', 'PATH', 'CWRAPPERS_CONFIG_DIR']
        names += ['EMBERBSD_DARWIN_SEED_' + role for role in ('CC', 'CXX', 'CPP', 'AS')]
        values = dict(zip(names, make(*[word for name in names
                                      for word in ('-V', '${' + name + '}')]).splitlines()))
        make('generate-wrappers' if backend == 'traditional' else 'generate-cwrappers')
        env['PATH'] = values['PATH']
        env['CWRAPPERS_CONFIG_DIR'] = values['CWRAPPERS_CONFIG_DIR']
        for role in ('CC', 'CXX', 'CPP', 'AS'):
            words = shlex.split(values[role])
            assert len(words) == 1, (backend, role, words)
            executable = wrapper_dir / 'bin' / Path(words[0]).name
            assert executable.is_file() and os.access(executable, os.X_OK), (backend, role, executable)
        assert len({values[role] for role in ('CC', 'CPP', 'AS')}) == 3, values

        (directory / 'answer.c').write_text('int ember_answer(void) { return 42; }\n')
        (directory / 'main.c').write_text('#include <stdio.h>\nint ember_answer(void);\n'
                                         'int main(void) { puts("wrapper-ok"); return ember_answer() != 42; }\n')
        (directory / 'cpp.c').write_text('#define WRAPPER_ANSWER 42\nWRAPPER_ANSWER\n')
        (directory / 'cxx.cc').write_text('static_assert(sizeof(int) >= 2, "int");\nint main() { return 0; }\n')
        calls = [('CC', ['-S', 'answer.c', '-o', 'answer.s']),
                 ('AS', ['answer.s', '-o', 'answer.o']),
                 ('CPP', ['-P', 'cpp.c']),
                 ('CC', ['main.c', 'answer.o', '-o', 'consumer']),
                 ('CXX', ['cxx.cc', '-o', 'cxx-consumer'])]
        for role, tail in calls:
            result = subprocess.run([*shlex.split(values[role]), *tail], cwd=directory,
                                    env=env, text=True, capture_output=True, timeout=30)
            assert result.returncode == 0, (backend, role, result.stdout, result.stderr)
            if role == 'CPP':
                assert result.stdout.strip() == '42', result.stdout
        for name, expected in (('consumer', 'wrapper-ok\n'), ('cxx-consumer', '')):
            result = subprocess.run([str(directory / name)], env=env, text=True,
                                    capture_output=True, timeout=10)
            assert result.returncode == 0 and result.stdout == expected, (backend, name, result)
        actual = [shlex.split(line.removeprefix('<.> '))
                  for line in (directory / 'commands.log').read_text().splitlines()
                  if line.startswith('<.> ')]
        assert len(actual) == len(calls), actual
        for (role, _), words in zip(calls, actual):
            selected = shlex.split(values['EMBERBSD_DARWIN_SEED_' + role])
            assert words[0] == selected[0], (role, words)
            expected_counts = Counter(selected[1:])
            actual_counts = Counter(words[1:])
            assert all(actual_counts[word] == count for word, count in expected_counts.items()), (role, words, selected)
            # Retain the selected tuple's order, including paired ABI and language arguments.
            assert any(words[i:i + len(selected) - 1] == selected[1:]
                       for i in range(1, len(words))), (role, words, selected)
        reports.append(dict(backend=backend, commands=actual, native_consumers=2))
    (work / 'result.json').write_text(json.dumps(reports, indent=2) + '\n')
    print('PASS: both real wrapper backends; 10 Clang commands, exact seed tails, CPP=42, four native consumers')


if __name__ == '__main__':
    main()
