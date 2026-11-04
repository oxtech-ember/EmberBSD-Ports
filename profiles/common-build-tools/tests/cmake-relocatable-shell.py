#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check relocated CMake's generated Unix Makefiles with producer denied.

Argument: an already-qualified native prefix containing cmake, gmake and mksh,
and the original producer prefix.  Copies only those standalone executables;
share/lib are read-only links to the qualified runtime, not an SDK clone.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

qualified, producer = (Path(p).resolve(strict=True) for p in sys.argv[1:])
if sys.platform != 'darwin':
    raise SystemExit('producer-denial regression requires Darwin sandbox-exec')
with tempfile.TemporaryDirectory(prefix='ember-cmake-shell-', dir='/private/tmp') as tmp:
    work = Path(tmp)
    prefix = work / 'runtime with spaces'
    (prefix / 'bin').mkdir(parents=True)
    for name in ('cmake', 'mksh'):
        shutil.copy2((qualified / 'bin' / name).resolve(strict=True), prefix / 'bin' / name)
    for name in ('share', 'lib'):
        (prefix / name).symlink_to(qualified / name, target_is_directory=True)
    alias = work / 'external-cmake'
    alias.symlink_to(prefix / 'bin/cmake')
    source = work / 'source'
    source.mkdir()
    (source / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.20)
project(native_shell NONE)
add_custom_target(probe ALL COMMAND "${CMAKE_COMMAND}" -E echo "shell runtime ok" VERBATIM)
''')
    escaped = str(producer).replace('\\', '\\\\').replace('"', '\\"')
    profile = '(version 1)(allow default)(deny file-read* (subpath "' + escaped + '"))'
    deny = ['/usr/bin/sandbox-exec', '-p', profile]
    proof = subprocess.run(deny + ['/bin/cat', str(producer / 'bin/cmake')],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if proof.returncode == 0:
        raise AssertionError('sandbox did not deny the producer')
    env = dict(os.environ, PATH=str(prefix / 'bin') + ':/usr/bin:/bin', LC_ALL='C')
    for name in ('CMAKE_PREFIX_PATH', 'CMAKE_MODULE_PATH', 'DYLD_LIBRARY_PATH', 'MAKEFLAGS', 'MFLAGS'):
        env.pop(name, None)

    def run(argv, *, success=True):
        p = subprocess.run(deny + list(map(str, argv)), cwd=work, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if (p.returncode == 0) != success:
            raise AssertionError(f'{argv}: exit {p.returncode}\\n{p.stdout}')
        return p.stdout

    for name, executable in (('direct', prefix / 'bin/cmake'), ('external-symlink', alias)):
        build = work / ('build-' + name)
        run([executable, '-S', source, '-B', build, '-G', 'Unix Makefiles',
             '-DCMAKE_MAKE_PROGRAM=' + str(qualified / 'bin/gmake')])
        makefile = (build / 'Makefile').read_text()
        expected = 'SHELL = ' + str(prefix / 'bin/mksh').replace(' ', '\\ ')
        if expected not in makefile:
            raise AssertionError('incorrect Makefile SHELL: ' + expected)
        try:
            result = run([executable, '--build', build])
        except AssertionError as e:
            lines = (build / 'Makefile').read_text().splitlines()
            raise AssertionError(str(e) + '\n' + '\n'.join(lines[75:100])) from e
        if 'shell runtime ok' not in result:
            raise AssertionError('build did not execute its recipe')
        print(name, 'generate+build PASS', flush=True)
    (prefix / 'bin/mksh').rename(prefix / 'bin/mksh.saved')
    output = run([prefix / 'bin/cmake', '-S', source, '-B', work / 'missing',
                  '-G', 'Unix Makefiles', '-DCMAKE_MAKE_PROGRAM=' + str(qualified / 'bin/gmake')], success=False)
    if 'Selected native shell is missing' not in output:
        raise AssertionError('missing provider failure was not explicit: ' + output)
    print('missing shell fails without fallback PASS')
