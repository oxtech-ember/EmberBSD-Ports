#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Replay the real optimized CMake pprof target with/without distinct frames."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'build', 'work', 'wrapper-config'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    environment = os.environ.copy()
    assert args.wrapper_config.is_dir()
    environment['CWRAPPERS_CONFIG_DIR'] = str(args.wrapper_config.resolve())
    source, build, work = (p.resolve() for p in (args.source, args.build, args.work))
    target = build / 'CMakeFiles/mimalloc-test-pprof.dir'
    flags_text = (target / 'flags.make').read_text()
    compiler = re.findall(r'^# compile C with (.+)$', flags_text, re.MULTILINE)
    assert len(compiler) == 1 and Path(compiler[0]).is_absolute()
    assert os.access(compiler[0], os.X_OK)
    flags = []
    for name in ('C_DEFINES', 'C_INCLUDES', 'C_FLAGS'):
        matches = re.findall(r'^' + name + r' = (.*)$', flags_text, re.MULTILINE)
        assert len(matches) == 1 and '$' not in matches[0]
        flags.extend(shlex.split(matches[0]))
    assert any(flag in ('-O2', '-O3') for flag in flags), 'use the optimized package build'
    link = shlex.split((target / 'link.txt').read_text())
    assert link and Path(link[0]).is_absolute() and link.count('-o') == 1
    object_name = 'CMakeFiles/mimalloc-test-pprof.dir/test/test-pprof.c.o'
    assert link.count(object_name) == 1 and 'libmimalloc.a' in link
    assert (build / 'libmimalloc.a').is_file()
    patched = (source / 'test/test-pprof.c').read_text()
    needle = 'static MI_TEST_NOINLINE void* alloc_site_##N('
    assert patched.count(needle) == 1, 'expected the canonical distinct-frame patch'
    baseline = patched.replace(needle, 'static void* alloc_site_##N(')
    work.mkdir(parents=True, exist_ok=False)
    assert patched.count('int created = 0;') == 1
    old_cleanup = patched.replace('      int created = 0;\n', '').replace('        if (result) { created++; }\n', '')
    old_cleanup = old_cleanup.replace('for (int t = 0; t < created; t++)',
                                      'for (int t = 0; t < MI_TEST_PPROF_THREAD_COUNT; t++)')
    results = []
    cases = (('without-noinline', baseline, 1, False, 'multiple distinct call sites'),
             ('patched', patched, 0, False, ''),
             ('old-create-failure', old_cleanup, 98, True, 'invalid join after create failure'),
             ('fixed-create-failure', patched, 1, True, 'thread safe with concurrently allocating/freeing threads'))
    for name, content, expected, inject_failure, marker in cases:
        case = work / name
        case.mkdir()
        (case / 'profile').mkdir()  # Match the upstream CMake test setup.
        fixture, obj, executable = (case / name for name in ('test-pprof.c', 'test-pprof.o', 'test-pprof'))
        fixture.write_text(content)
        extra_objects = []
        extra_flags = []
        if inject_failure:
            wrapper = case / 'thread-failure.c'
            wrapper.write_text("#include <pthread.h>\n#include <errno.h>\n#include <stdio.h>\n#include <stdlib.h>\n"
                "int probe_create(pthread_t* t, const pthread_attr_t* a, void* (*f)(void*), void* p) {\n"
                "  (void)t; (void)a; (void)f; (void)p; return EAGAIN;\n}\n"
                "int probe_join(pthread_t t, void** p) {\n"
                "  (void)t; (void)p; fputs(\"invalid join after create failure\\n\", stderr); _Exit(98);\n}\n")
            wrapper_object = case / 'thread-failure.o'
            argv = [compiler[0], *flags, '-c', str(wrapper), '-o', str(wrapper_object)]
            process = subprocess.run(argv, cwd=build, env=environment, capture_output=True, text=True)
            (case / 'wrapper-compile.log').write_text(process.stdout + process.stderr)
            assert process.returncode == 0, process.stdout + process.stderr
            extra_objects = [str(wrapper_object)]
            extra_flags = ['-Dpthread_create=probe_create', '-Dpthread_join=probe_join']
        compile_command = [compiler[0], *flags, *extra_flags, '-I' + str(source / 'test'), '-c', str(fixture), '-o', str(obj)]
        link_command = [str(obj) if part == object_name else part for part in link]
        link_command[link_command.index('-o') + 1] = str(executable)
        link_command.extend(extra_objects)
        commands = []
        for action, argv, cwd in (('compile', compile_command, build), ('link', link_command, build),
                                  ('run', [str(executable)], case)):
            process = subprocess.run(argv, cwd=cwd, env=environment, capture_output=True, text=True)
            output = process.stdout + process.stderr
            (case / (action + '.log')).write_text(output)
            commands.append({'action': action, 'argv': argv, 'cwd': str(cwd), 'exit_code': process.returncode})
            (case / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
            if action != 'run':
                assert process.returncode == 0, output
            else:
                assert process.returncode == expected, output
                if expected:
                    assert marker in output, output
                    if expected == 1:
                        assert re.search(r'^failed\s*: 1$', output, re.MULTILINE)
                else:
                    assert re.search(r'^succeeded: 8$', output, re.MULTILINE)
                    assert re.search(r'^failed\s*: 0$', output, re.MULTILINE)
        results.append({'case': name, 'exit_code': expected})
    (work / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
    print('Pprof passed all 8 checks; removing noinline or the created-thread guard reproduced both causal failures.')


if __name__ == '__main__':
    main()
