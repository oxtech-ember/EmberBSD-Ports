#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise optional TAPI through actual compiler-file serialization and reload."""
import argparse
import json
import os
from pathlib import Path
import subprocess

LANGUAGES = ('C', 'CXX', 'ASM', 'Fortran', 'HIP', 'OBJC', 'OBJCXX')


def quote(value):
    value = str(value)
    assert ']==]' not in value
    return '[==[' + value + ']==]'


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('cmake', 'cmake-source', 'baseline-source', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--configure-input', type=Path,
        help='JSON with explicit CMake arguments and environment for real C/CXX configure')
    args = cli.parse_args()
    for path in (args.cmake, args.cmake_source, args.baseline_source):
        assert path.is_absolute() and path.exists(), path
    assert os.access(args.cmake, os.X_OK)
    args.work.mkdir()
    policy = args.cmake_source / 'Modules/Platform/EmberBSD-DarwinTools.cmake'
    nonexec = args.work / 'non-executable'
    nonexec.write_text('Invalid tool fixture; never executed.\n')
    count = 0

    def run(label, command, expected=None, env=None):
        nonlocal count
        result = subprocess.run(command, cwd=args.work, env=env,
                                text=True, capture_output=True, timeout=120)
        (args.work / (label + '.stdout')).write_text(result.stdout)
        (args.work / (label + '.stderr')).write_text(result.stderr)
        if expected:
            assert result.returncode and expected in result.stderr, (label, result.stdout, result.stderr)
        else:
            assert result.returncode == 0, (label, result.stdout, result.stderr)
        count += 1

    def script(label, body, expected=None):
        path = args.work / (label + '.cmake')
        path.write_text('cmake_minimum_required(VERSION 4.4)\n' + body)
        run(label, [str(args.cmake), '-P', str(path)], expected)

    initial = ('set(EMBERBSD_CMAKE_NATIVE_TOOLS ON)\nset(CMAKE_HOST_APPLE TRUE)\n'
               'set(CMAKE_SYSTEM_NAME Darwin)\nset(EMBERBSD_DARWIN_TOOL_PHASE initial)\n')
    include_policy = 'include(' + quote(policy) + ')\n'
    for label, setup, expected in (
        ('initial-absent', initial, 'absent'),
        ('initial-apple', initial + 'set(EMBERBSD_DARWIN_TAPI_KIND apple)\n'
            + 'set(CMAKE_TAPI ' + quote(args.cmake) + ')\n', 'selected'),
        ('initial-llvm', initial + 'set(EMBERBSD_DARWIN_TAPI_KIND llvm-readtapi)\n'
            + 'set(CMAKE_TAPI ' + quote(args.cmake) + ')\n', 'selected'),
        ('full-absent', initial + 'set(EMBERBSD_DARWIN_TOOL_PHASE full)\n', 'empty'),
        ('non-darwin', initial + 'set(CMAKE_SYSTEM_NAME Linux)\n', 'empty'),
        ('ordinary', initial + 'set(EMBERBSD_CMAKE_NATIVE_TOOLS OFF)\n', 'empty'),
    ):
        for lang in LANGUAGES:
            template = args.cmake_source / ('Modules/CMake' + lang + 'Compiler.cmake.in')
            output = args.work / (label + '-' + lang + '-compiler.cmake')
            body = setup + include_policy
            body += 'configure_file(' + quote(template) + ' ' + quote(output) + ' @ONLY)\n'
            # The persisted file is loaded both during language initialization
            # and on reconfigure. Neither may invent an explicit empty selector.
            body += 'include(' + quote(output) + ')\n' + include_policy
            body += 'include(' + quote(output) + ')\n' + include_policy
            if expected == 'absent':
                body += 'if(DEFINED CMAKE_TAPI)\nmessage(FATAL_ERROR "TAPI absence was lost")\nendif()\n'
            elif expected == 'selected':
                body += 'if(NOT CMAKE_TAPI STREQUAL ' + quote(args.cmake) + ')\nmessage(FATAL_ERROR "Selected TAPI changed")\nendif()\n'
            else:
                body += 'if(NOT DEFINED CMAKE_TAPI OR NOT CMAKE_TAPI STREQUAL "")\nmessage(FATAL_ERROR "Upstream empty serialization changed")\nendif()\n'
            script(label + '-' + lang, body)

    # The original C template must reproduce the reported C -> CXX failure.
    original = args.baseline_source / 'Modules/CMakeCCompiler.cmake.in'
    output = args.work / 'baseline-compiler.cmake'
    body = initial + include_policy
    body += 'configure_file(' + quote(original) + ' ' + quote(output) + ' @ONLY)\n'
    body += 'include(' + quote(output) + ')\n' + include_policy
    script('baseline-reload', body, 'CMAKE_TAPI must select an existing absolute executable')

    for label, value in (('empty', ''), ('relative', 'tapi'),
                         ('missing', args.work / 'missing'), ('directory', args.work),
                         ('nonexec', nonexec), ('notfound', 'CMAKE_TAPI-NOTFOUND')):
        body = initial + 'set(CMAKE_TAPI ' + quote(value) + ')\n' + include_policy
        script('invalid-' + label, body, 'CMAKE_TAPI must select an existing absolute executable')
    for kind in (None, 'unknown'):
        body = initial + 'set(CMAKE_TAPI ' + quote(args.cmake) + ')\n'
        if kind:
            body += 'set(EMBERBSD_DARWIN_TAPI_KIND ' + quote(kind) + ')\n'
        script('invalid-kind-' + str(kind), body + include_policy,
               'CMAKE_TAPI requires EMBERBSD_DARWIN_TAPI_KIND')

    if args.configure_input:
        record = json.loads(args.configure_input.read_text())
        assert set(record) == {'arguments', 'environment'}
        assert isinstance(record['arguments'], list) and isinstance(record['environment'], dict)
        for label, source, error in (
            ('configure-baseline', args.baseline_source,
             'CMAKE_TAPI must select an existing absolute executable'),
            ('configure-fixed', args.cmake_source, None),
        ):
            project = args.work / (label + '-source')
            project.mkdir()
            # Bootstrap CMake has a compiled-in module root. Only the template
            # input root is overlaid for this isolated regression; its compiler
            # detection and platform policy execute from the real bootstrap.
            (project / 'CMakeLists.txt').write_text(
                'cmake_minimum_required(VERSION 4.4)\n'
                'set(CMAKE_ROOT ' + quote(source) + ')\n'
                'project(EmberInitialReload LANGUAGES C CXX)\n'
                'if(DEFINED CMAKE_TAPI)\nmessage(FATAL_ERROR "Unexpected TAPI selector")\nendif()\n')
            build = args.work / (label + '-build')
            command = [str(args.cmake), '-S', str(project), '-B', str(build),
                       *record['arguments']]
            run(label, command, error, record['environment'])
            if not error:
                cache = (build / 'CMakeCache.txt').read_text()
                assert 'CMAKE_TAPI:' not in cache
                run(label + '-reload', command, env=record['environment'])
                for lang in ('C', 'CXX'):
                    files = list((build / 'CMakeFiles').glob('*/CMake' + lang + 'Compiler.cmake'))
                    assert len(files) == 1 and 'set(CMAKE_' + lang + '_COMPILER_WORKS TRUE)' in files[0].read_text()
    print(f'PASS: {count} actual CMake controls; template reload is not a TAPI operation or package build')


if __name__ == '__main__':
    main()
