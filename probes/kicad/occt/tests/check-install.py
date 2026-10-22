#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Execute actual OCCT CMake install fragments.
"""Check installed scripts, DESTDIR, and first/repeated third-party configuration."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quote(value):
    return '"' + str(value).replace('\\', '/').replace('$', '\\$').replace('"', '\\"') + '"'


def between(text, start, finish):
    first = text.index(start)
    return text[first:text.index(finish, first)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('patched', type=Path)
    parser.add_argument('work', type=Path)
    parser.add_argument('--recipe', type=Path, required=True, help='Canonical cad/occt/Makefile')
    parser.add_argument('--cmake', default=os.environ.get('CMAKE', 'cmake'))
    args = parser.parse_args()
    original, patched, recipe = (p.resolve(strict=True) for p in (args.original, args.patched, args.recipe))
    work = args.work.resolve()
    require(args.work.is_absolute() and work == args.work and not work.exists() and not work.is_symlink(),
            'Use a new absolute canonical work directory.')
    require(not any(work.is_relative_to(p) for p in (original, patched, recipe.parent)),
            'Keep test output outside the source and recipe inputs.')
    # Read the actual recipe argument. Do not supply an independent test-only fix.
    arguments = []
    for line in recipe.read_text().splitlines():
        match = re.fullmatch(r'CMAKE_CONFIGURE_ARGS\s*\+?=\s*(.*)', line)
        if match:
            arguments.extend(arg for arg in shlex.split(match[1], comments=True)
                             if arg.startswith('-D3RDPARTY_DIR'))
    require(arguments == ['-D3RDPARTY_DIR:PATH='],
            'The recipe must set exactly one explicit empty 3RDPARTY_DIR PATH.')
    inputs = [recipe]
    for source in (original, patched):
        inputs.extend(source / relative for relative in (
            'CMakeLists.txt', 'adm/cmake/occt_macros.cmake',
            'adm/templates/custom.sh.main', 'adm/templates/env.install.sh.in'))
    hashes = {str(path): digest(path) for path in inputs}
    work.mkdir(parents=True)
    temporary = work / 'tmp'
    temporary.mkdir()
    environment = dict(os.environ, TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary))
    records = []

    def run(name, argv, extra=None):
        argv = list(map(str, argv))
        result = subprocess.run(argv, env=environment | (extra or {}), capture_output=True)
        (work / (name + '.log')).write_bytes(result.stdout + result.stderr)
        records.append(dict(name=name, argv=argv, status=result.returncode))
        (work / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
        require(result.returncode == 0, name + ' failed; inspect its log.')

    for variant, source in (('before', original), ('after', patched)):
        main_source = (source / 'CMakeLists.txt').read_text()
        custom_block = between(main_source, 'if (WIN32)\n  set (ADDITIONAL_CUSTOM_CONTENT',
                               'if (WIN32)\n  set (THIRDPARTY_DIR_REPLACE')
        flag_lines = [line for line in main_source.splitlines(keepends=True)
                      if re.match(r'^install \(CODE.*(?:TOLOWER|file\(INSTALL FILES).*CMAKE_INSTALL_CONFIG_NAME', line)]
        require(len(flag_lines) == 2, 'Missing exact upstream flags install statements.')
        project, build, prefix, stage = (work / variant / name for name in ('source', 'build', 'prefix', 'stage'))
        for path in (project, build, prefix / 'bin', stage):
            path.mkdir(parents=True)
        # These are installation inputs, not libraries or replacement OCCT code.
        (build / 'custom.sh').write_text('existing build script\n')
        expected = '\nif [ -e "${aScriptPath}/custom_gcc_64.sh" ]; then\n  source "${aScriptPath}/custom_gcc_64.sh" "$1" "$2" \nfi'
        sentinel = prefix / 'bin/custom.sh'
        sentinel.write_text(expected)
        sentinel_hash = digest(sentinel)
        (build / 'OpenCASCADECompileDefinitionsAndFlags-release.cmake').write_text('set(OCCT_INSTALL_FIXTURE ON)\n')
        (project / 'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.22)
project(occt_install_source_contract NONE)
set(OCCT_ROOT_DIR {quote(source)})
set(OCCT_BINARY_DIR {quote(build)})
set(INSTALL_DIR {quote(prefix)})
set(CMAKE_INSTALL_PREFIX {quote(prefix)})
set(INSTALL_DIR_SCRIPT bin)
set(INSTALL_DIR_CMAKE lib/cmake/opencascade)
set(SCRIPT_EXT sh)
set(SUB_CUSTOM_NAME custom_gcc_64.sh)
include({quote(source / 'adm/cmake/occt_macros.cmake')})
''' + custom_block + ''.join(flag_lines))
        run(variant + '-configure', [args.cmake, '-S', project, '-B', build])
        run(variant + '-install', [args.cmake, '--install', build, '--config', 'Release'], {'DESTDIR': str(stage)})
        require(digest(sentinel) == sentinel_hash, 'Installed prefix was modified.')
        files = {path for path in stage.rglob('*') if path.is_file()}
        expected_flags = stage / prefix.relative_to(prefix.anchor) / 'lib/cmake/opencascade/OpenCASCADECompileDefinitionsAndFlags-release.cmake'
        require(expected_flags in files, 'Compile-definitions file escaped the single DESTDIR boundary.')
        custom = stage / prefix.relative_to(prefix.anchor) / 'bin/custom.sh'
        if variant == 'before':
            require(not custom.exists(), 'Baseline unexpectedly installed custom.sh.')
            require(files == {expected_flags}, 'Unexpected baseline payload.')
        else:
            require(custom.is_file() and expected in custom.read_text(), 'Patched custom.sh is missing or incorrect.')
            require(files == {expected_flags, custom}, 'Unexpected patched payload.')

    # Upstream used different normal/cache values on the first and next configure.
    marker = '# Set 3RDPARTY_DIR based on layout'
    end = '# search for CSF variable in EXTERNLIB'
    original_block = between((original / 'CMakeLists.txt').read_text(), marker, end)
    patched_block = between((patched / 'CMakeLists.txt').read_text(), marker, end)
    require(original_block == patched_block, 'The recipe regression requires the unchanged upstream block.')
    thirdparty = {}
    for variant, source, flags in (('default-root', original, []), ('recipe-root', patched, arguments)):
        project, build = (work / variant / name for name in ('source', 'build'))
        project.mkdir(parents=True)
        (project / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.22)
project(occt_thirdparty_source_contract NONE)
set(LAYOUT_IS_VCPKG FALSE)
set(BUILD_USE_VCPKG OFF)
set(3RDPARTY_DIR_DESCR "Third-party root")
''' + original_block + f'''
configure_file({quote(source / 'adm/templates/env.install.sh.in')} "${{CMAKE_BINARY_DIR}}/env.install.sh" @ONLY)
file(WRITE "${{CMAKE_BINARY_DIR}}/thirdparty.txt" "${{3RDPARTY_DIR}}")
''')
        values = []
        for phase in ('first', 'repeat'):
            run(variant + '-' + phase, [args.cmake, '-S', project, '-B', build, *flags])
            value = (build / 'thirdparty.txt').read_text()
            values.append(value)
            shell = (build / 'env.install.sh').read_text()
            require('export THIRDPARTY_DIR="' + value + '"' in shell,
                    'The shell template does not use the configured third-party root.')
            for filename in ('CMakeCache.txt', 'env.install.sh'):
                (work / f'{variant}-{phase}-{filename}').write_bytes((build / filename).read_bytes())
        expected_values = [str(project), ''] if variant == 'default-root' else ['', '']
        require(values == expected_values, variant + ' did not expose or repair the first/repeated configure difference.')
        thirdparty[variant] = values
    require(hashes == {str(path): digest(path) for path in inputs}, 'A source or recipe input changed during the check.')
    (work / 'results.json').write_text(json.dumps(dict(
        status='pass', inputs=hashes, commands=records, thirdparty=thirdparty,
        scope='Actual source CMake fragments and templates. No target build, link, package or runtime acceptance.'), indent=2) + '\n')
    print('PASS: custom.sh omission and repair; one DESTDIR; first/repeated third-party root.')


if __name__ == '__main__':
    main()
