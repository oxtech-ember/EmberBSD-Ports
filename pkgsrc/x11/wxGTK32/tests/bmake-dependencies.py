#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the shared Bakefile emitter and bmake's incremental dependencies."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'bmake', 'autoconf', 'shell'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
for name in ('source', 'bmake', 'autoconf', 'shell'):
    setattr(a, name, getattr(a, name).resolve(strict=True))


def dependency_emitter(text):
    start = text.index('    if test "x$bakefile_cv_prog_makeisgnu" = "xyes"; then')
    end = text.index('\n    fi\n', start) + len('\n    fi\n')
    return text[start:end]


with tempfile.TemporaryDirectory(prefix='wx-bmake-dependencies-') as tmp:
    root = Path(tmp).resolve()
    (root / 'bakefile.m4').write_bytes((a.source / 'build/aclocal/bakefile.m4').read_bytes())
    templates = ('Makefile', 'utils/wxrc/Makefile', 'tests/Makefile')
    (root / 'configure.ac').write_text(
        'AC_INIT([wx-dependencies-contract], [1])\n'
        'm4_include([bakefile.m4])\nAC_BAKEFILE_GNUMAKE\n'
        'AC_CONFIG_FILES([' + ' '.join(templates) + '])\nAC_OUTPUT\n')
    for name in templates:
        upstream = (a.source / (name + '.in')).read_text()
        directive = '@IF_GNU_MAKE@-include ./.deps/*.d'
        assert upstream.count(directive) == 1, name
        template = root / (name + '.in')
        template.parent.mkdir(parents=True, exist_ok=True)
        template.write_text(
            'all: changed.o unchanged.o sub/nested.o\n'
            'changed.o: changed.c\n\t@echo REBUILD changed\n'
            'unchanged.o: unchanged.c\n\t@echo REBUILD unchanged\n'
            'sub/nested.o: sub/nested.c\n\t@echo REBUILD nested\n' + directive + '\n')
    env = dict(os.environ, MAKE=str(a.bmake), SHELL=str(a.shell), CONFIG_SHELL=str(a.shell))
    subprocess.run([str(a.autoconf)], cwd=root, env=env, check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Keep the shipped configure synchronized with its source macro, including
    # m4 quoting of sinclude (which is also an m4 builtin).
    assert dependency_emitter((root / 'configure').read_text()) == dependency_emitter(
        (a.source / 'configure').read_text())
    subprocess.run([str(a.shell), './configure'], cwd=root, env=env, check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for name in templates:
        directory = (root / name).parent
        for stem in ('changed', 'unchanged', 'sub/nested'):
            source = directory / (stem + '.c')
            header = directory / (stem + '.inc')
            obj = directory / (stem + '.o')
            source.parent.mkdir(exist_ok=True)
            source.write_text('source\n'); header.write_text('header\n'); obj.write_text('object\n')
            for path, stamp in ((source, 100), (header, 100), (obj, 200)):
                os.utime(path, (stamp, stamp))
            deps = obj.parent / '.deps'; deps.mkdir(exist_ok=True)
            (deps / (obj.name + '.d')).write_text(
                stem + '.o: ' + stem + '.c ' + stem + '.inc\n')
        command = [str(a.bmake), '-r', '-n', '-f', 'Makefile', 'all']
        result = subprocess.run(command, cwd=directory, env=env, check=True,
                                capture_output=True, text=True)
        assert 'REBUILD' not in result.stdout, (name, result.stdout)
        for stem in ('changed', 'sub/nested'):
            header = directory / (stem + '.inc')
            header.write_text('changed header\n'); os.utime(header, (300, 300))
        result = subprocess.run(command, cwd=directory, env=env, check=True,
                                capture_output=True, text=True)
        assert 'REBUILD changed' in result.stdout and 'REBUILD nested' in result.stdout, (name, result.stdout)
        assert 'REBUILD unchanged' not in result.stdout, (name, result.stdout)
        # A clean first build has no compiler depfiles yet.
        for dep in directory.glob('**/.deps/*.d'):
            dep.unlink()
        for stem in ('changed', 'unchanged', 'sub/nested'):
            (directory / (stem + '.o')).unlink()
        result = subprocess.run(command, cwd=directory, env=env, check=True,
                                capture_output=True, text=True)
        assert all('REBUILD ' + name in result.stdout for name in ('changed', 'unchanged', 'nested'))
print('PASS: shared emitter configures main/wxrc/tests; bmake rebuilds only changed dependencies, including nested objects; missing depfiles are accepted')
