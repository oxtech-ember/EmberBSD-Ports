#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Build two real Darwin ASM consumers and count their generated-file writers."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def quote(value):
    assert ']==]' not in str(value)
    return '[==[' + str(value) + ']==]'


def block(text, begin, end):
    start = text.index(begin)
    return text[start:text.index(end, start)]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('cmake', 'source', 'baseline-source', 'configure-input', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--jobs', type=int, default=18)
    args = cli.parse_args()
    assert 2 <= args.jobs <= 18
    record = json.loads(args.configure_input.read_text())
    assert set(record) == {'arguments', 'environment'}
    args.work.mkdir()
    relay = args.work / 'record-cmake'
    relay.write_text('#!' + sys.executable + '\n' +
        'import json,os,subprocess,sys,time\n'
        'assert sys.argv[1:3] == ["-E", "create_symlink"], sys.argv\n'
        'fd=os.open(os.environ["WRITER_LOG"],os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)\n'
        'os.write(fd,(json.dumps({"output":sys.argv[-1],"pid":os.getpid()})+"\\n").encode());os.close(fd)\n'
        '# Widen the scheduling window without replacing the real CMake operation.\n'
        'time.sleep(0.02)\n'
        'sys.exit(subprocess.call([' + repr(str(args.cmake)) + ']+sys.argv[1:]))\n')
    relay.chmod(0o755)

    def run(label, command, environment):
        result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=120)
        (args.work / (label + '.stdout')).write_text(result.stdout)
        (args.work / (label + '.stderr')).write_text(result.stderr)
        return result

    def fixture(source, label, arch='arm64'):
        project = args.work / (label + '-source')
        project.mkdir()
        builtins = source / 'compiler-rt/lib/builtins'
        (project / 'aarch64').mkdir()
        for name in ('aarch64/lse.S', 'assembly.h', 'int_endianness.h'):
            shutil.copy2(builtins / name, project / name)
        generation = block((builtins / 'CMakeLists.txt').read_text(),
                           '# Generate outline atomics helpers', '\nif (MINGW)')
        darwin = (source / 'compiler-rt/cmake/Modules/CompilerRTDarwinUtils.cmake').read_text()
        macro = block(darwin, 'macro(darwin_add_builtin_library ', '\nendmacro()') + '\nendmacro()\n'
        start = next(line for line in darwin.splitlines() if 'if(' in line and 'arm64 IN_LIST DARWIN_BUILTIN_ARCHS' in line)
        dependency = block(darwin, start, '    foreach (arch ${DARWIN_BUILTIN_ARCHS})')
        utils = (source / 'compiler-rt/cmake/Modules/CompilerRTUtils.cmake').read_text()
        flags = block(utils, 'function(set_target_compile_flags ', '\nendfunction()') + '\nendfunction()\n'
        contents = ('cmake_minimum_required(VERSION 4.4)\nproject(OutlineWriters C ASM)\n'
            'set(COMPILER_RT_OUTPUT_LIBRARY_DIR "${CMAKE_BINARY_DIR}/out")\n'
            'file(MAKE_DIRECTORY "${COMPILER_RT_OUTPUT_LIBRARY_DIR}")\n'
            'set(_selected_cmake "${CMAKE_COMMAND}")\nset(CMAKE_COMMAND ' + quote(relay) + ')\n'
            + generation + '\nset(CMAKE_COMMAND "${_selected_cmake}")\n'
            + flags + macro + '\nset(DARWIN_BUILTIN_ARCHS ' + arch + ')\n' + dependency
            + '\nlist(GET aarch64_SOURCES 0 sample)\nadd_custom_target(consumers ALL)\n')
        for suffix in ('builtins', 'cc_kext'):
            contents += ('darwin_add_builtin_library(clang_rt ' + suffix + '\n'
                '  OS osx ARCH ' + arch + ' DEPS ${deps_' + arch + '} SOURCES ${sample}\n'
                '  CFLAGS -arch ' + arch + ' PARENT_TARGET consumers)\n'
                'get_target_property(deps clang_rt.' + suffix + '_' + arch + '_osx MANUALLY_ADDED_DEPENDENCIES)\n'
                'file(APPEND "${CMAKE_BINARY_DIR}/consumer-dependencies.txt" "${deps}\\n")\n')
        (project / 'CMakeLists.txt').write_text(contents)
        return project

    def build(label, build_dir, expect_success=True):
        log = args.work / (label + '.writers.jsonl')
        environment = dict(record['environment'], WRITER_LOG=str(log))
        result = run(label, [str(args.cmake), '--build', str(build_dir), '--parallel', str(args.jobs)], environment)
        if expect_success:
            assert result.returncode == 0, (result.stdout, result.stderr)
        else:
            assert result.returncode == 0 or 'File exists' in result.stdout + result.stderr, (result.stdout, result.stderr)
        return Counter(Path(json.loads(line)['output']).name for line in log.read_text().splitlines()) if log.exists() else Counter()

    evidence = {}
    for label, source in (('baseline', args.baseline_source), ('fixed', args.source)):
        project = fixture(source, label)
        build_dir = args.work / (label + '-build')
        result = run(label + '-configure', [str(args.cmake), '-S', str(project), '-B', str(build_dir),
                    *record['arguments']], record['environment'])
        assert result.returncode == 0, (result.stdout, result.stderr)
        counts = build(label, build_dir, label == 'fixed')
        evidence[label] = dict(counts)
        if label == 'baseline':
            assert any(value > 1 for value in counts.values()), counts
            continue
        assert len(counts) == 125 and set(counts.values()) == {1}, counts
        dependencies = (build_dir / 'consumer-dependencies.txt').read_text().splitlines()
        assert dependencies == ['lse_builtin_symlinks', 'lse_builtin_symlinks'], dependencies
        helpers = build_dir / 'outline_atomic_helpers.dir'
        assert all((helpers / name).is_symlink() and (helpers / name).resolve() == project / 'aarch64/lse.S' for name in counts)
        archives = list(build_dir.glob('libclang_rt.*_arm64_osx.a'))
        assert len(archives) == 2, archives
        ar = next(v.split('=', 1)[1] for v in record['arguments'] if v.startswith('-DCMAKE_AR:'))
        for archive in archives:
            members = run('archive-' + archive.stem, [ar, 't', str(archive)], record['environment'])
            assert members.returncode == 0 and 'outline_atomic_cas1_1.S.o' in members.stdout, members
        assert not build('fixed-noop', build_dir)
        (helpers / 'outline_atomic_cas1_1.S').unlink()
        assert build('fixed-regenerate', build_dir) == Counter({'outline_atomic_cas1_1.S': 1})

    # These Darwin aliases share the producer, but this macOS test does not
    # claim arm64e/watchOS execution or compile their archives with macOS headers.
    for arch in ('arm64e', 'arm64_32'):
        project = fixture(args.source, arch, arch)
        build_dir = args.work / (arch + '-build')
        result = run(arch + '-configure', [str(args.cmake), '-S', str(project), '-B', str(build_dir),
                    *record['arguments']], record['environment'])
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert (build_dir / 'consumer-dependencies.txt').read_text().splitlines() == ['lse_builtin_symlinks'] * 2
    (args.work / 'result.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'PASS: make -j{args.jobs}: baseline duplicates writers; fixed generates each of 125 helpers once, builds both ASM archives, and regenerates a missing helper once')


if __name__ == '__main__':
    main()
