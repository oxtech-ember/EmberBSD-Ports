#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise compiler-rt's real Darwin archive rules with explicit tool inputs."""
import argparse
import json
from pathlib import Path
import subprocess


def quote(value):
    assert ']==]' not in str(value)
    return '[==[' + str(value) + ']==]'


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('cmake', 'source', 'configure-input', 'libtool', 'baseline-libtool', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    args = cli.parse_args()
    record = json.loads(args.configure_input.read_text())
    assert set(record) == {'arguments', 'environment'}
    args.work.mkdir()
    project = args.work / 'source'
    project.mkdir()
    module = args.source / 'compiler-rt/cmake/Modules/UseLibtool.cmake'
    assert module.is_file()
    (project / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 4.4)\nproject(RuntimeArchive C)\n'
        'include(' + quote(module) + ')\nadd_library(runtime_archive STATIC archive.c)\n')
    (project / 'archive.c').write_text('int runtime_archive_value(void) { return 23; }\n')

    def run(label, command):
        result = subprocess.run(command, env=record['environment'], capture_output=True,
                                text=True, timeout=120)
        (args.work / (label + '.log')).write_text(result.stdout + result.stderr)
        return result

    for label, libtool in (('baseline', args.baseline_libtool), ('selected', args.libtool)):
        build = args.work / (label + '-build')
        result = run(label + '-configure', [str(args.cmake), '-S', str(project), '-B', str(build),
            *record['arguments'], '-DCMAKE_LIBTOOL:FILEPATH=' + str(libtool)])
        assert result.returncode == 0, result.stdout + result.stderr
        # Check the actual rule, not only the CMake cache value.
        link = (build / 'CMakeFiles/runtime_archive.dir/link.txt').read_text()
        assert '"' + str(libtool) + '" -static ' in link, link
        result = run(label + '-build', [str(args.cmake), '--build', str(build), '--parallel', '2'])
        if label == 'baseline':
            assert result.returncode != 0 and 'Missing --mode=' in result.stdout + result.stderr, result
        else:
            assert result.returncode == 0, result.stdout + result.stderr
            archive = build / 'libruntime_archive.a'
            ar = next(value.split('=', 1)[1] for value in record['arguments']
                      if value.startswith('-DCMAKE_AR:'))
            members = run('archive-members', [ar, 't', str(archive)])
            names = [name for name in members.stdout.splitlines() if not name.startswith('__.SYMDEF')]
            assert members.returncode == 0 and names == ['archive.c.o'], members
    print('PASS: actual compiler-rt archive rule rejects GNU wrapper and builds with selected LLVM Darwin libtool')


if __name__ == '__main__':
    main()
