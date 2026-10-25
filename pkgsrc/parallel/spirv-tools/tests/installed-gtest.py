#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check actual test-provider selection with CMake LANGUAGES NONE."""
import argparse
import hashlib
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tarfile
import tempfile

RECIPE = Path(__file__).resolve().parents[1]
COMPONENTS = ('gtest', 'gtest_main', 'gmock', 'gmock_main')


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cmake', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--patch', type=Path, required=True)
    parser.add_argument('--work-parent', type=Path, required=True)
    args = parser.parse_args()
    require(all(path.is_absolute() for path in vars(args).values()), 'Use absolute input paths')
    data = args.archive.read_bytes()
    distinfo = (RECIPE / 'distinfo').read_text()
    for label, algorithm in (('BLAKE2s', 'blake2s'), ('SHA512', 'sha512')):
        expected = re.search(r'^' + label + r' \(SPIRV-Tools-2026\.4.tar.gz\) = ([0-9a-f]+)$', distinfo, re.M)
        require(expected and hashlib.new(algorithm, data).hexdigest() == expected[1], 'Archive hash mismatch')
    patch = RECIPE / 'patches/patch-installed-gtest'
    patch_sha1 = runpy.run_path(str(RECIPE.parents[2] / 'scripts/prepare-pkgsrc.py'))['patch_sha1']
    require(patch_sha1(patch) == re.search(
        r'^SHA1 \(patch-installed-gtest\) = ([0-9a-f]+)$', distinfo, re.M)[1], 'Patch hash mismatch')
    print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True), end='')
    work = Path(tempfile.mkdtemp(prefix='spirv-installed-gtest-', dir=args.work_parent))
    try:
        source = work / 'source'
        with tarfile.open(args.archive) as archive:
            texts = {}
            for name in ('CMakeLists.txt', 'external/CMakeLists.txt', 'test/CMakeLists.txt'):
                texts[name] = archive.extractfile('SPIRV-Tools-2026.4/' + name).read().decode()
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True); path.write_text(texts[name])
        result = subprocess.run([str(args.patch), '-F', '0', '-p0', '-i', str(patch)],
                                cwd=source, capture_output=True, text=True)
        require(result.returncode == 0 and not re.search(r'fuzz|offset', result.stdout, re.I),
                'Source patch did not apply exactly: ' + result.stdout + result.stderr)
        root_text = (source / 'CMakeLists.txt').read_text()
        start = root_text.index('option(SPIRV_USE_INSTALLED_GTEST')
        fragment = root_text[start:root_text.index('# Defaults to ON.', start)]
        external = (source / 'external/CMakeLists.txt').read_text()
        helpers = external[:external.index('if (DEFINED mimalloc_SOURCE_DIR)')]
        start = external.index('if (NOT ${SPIRV_SKIP_TESTS})')
        external = helpers + external[start:external.index('if(SPIRV_BUILD_FUZZER)', start)]
        test = texts['test/CMakeLists.txt']
        test = test[test.index('if (${SPIRV_SKIP_TESTS})'):test.index('function(add_spvtools_unittest)')]
        test += '\nforeach(component gtest gtest_main gmock gmock_main effcee re2)\n' \
                '  if(NOT TARGET ${component})\n' \
                '    message(FATAL_ERROR "sibling test cannot see ${component}")\n' \
                '  endif()\nendforeach()\nfile(WRITE "${CMAKE_BINARY_DIR}/unit-metadata" "present")\n'
        test += 'if(SPIRV_USE_INSTALLED_GTEST)\n' \
                '  set(_expected_gtest_system_option "SHELL:-isystem \\\"${_test_gtest_include_dir}\\\"")\n' \
                '  foreach(component gtest gtest_main gmock gmock_main)\n' \
                '    get_target_property(_gtest_options GTest::${component} INTERFACE_COMPILE_OPTIONS)\n' \
                '    if(_test_expect_gtest_system_option AND NOT _expected_gtest_system_option IN_LIST _gtest_options)\n' \
                '      message(FATAL_ERROR "${component} lost the imported SYSTEM include")\n' \
                '    elseif(NOT _test_expect_gtest_system_option AND _expected_gtest_system_option IN_LIST _gtest_options)\n' \
                '      message(FATAL_ERROR "${component} received an unnecessary SYSTEM include")\n' \
                '    endif()\n' \
                '  endforeach()\nendif()\n'
        prefix = work / 'isolated/lib/cmake/GTest'
        prefix.mkdir(parents=True)
        include_dir = work / 'isolated include'
        include_dir.mkdir()
        (prefix / 'GTestConfigVersion.cmake').write_text(
            'set(PACKAGE_VERSION 1.18.0)\nset(PACKAGE_VERSION_COMPATIBLE TRUE)\n')
        effcee_prefix, re2_prefix = [work / ('isolated/lib/cmake/' + name) for name in ('effcee', 're2')]
        for path in (effcee_prefix, re2_prefix):
            path.mkdir(parents=True)
        (effcee_prefix / 'effceeConfigVersion.cmake').write_text(
            'set(PACKAGE_VERSION 1.2026.0)\nset(PACKAGE_VERSION_COMPATIBLE TRUE)\n')

        def configure(name, installed, components=COMPONENTS, *, skip=False, fault=None, valid=True, error=''):
            fixture = work / name
            (fixture / 'external/googletest').mkdir(parents=True)
            (fixture / 'test').mkdir()
            (prefix / 'GTestConfig.cmake').write_text(''.join(
                'add_library(GTest::' + component + ' INTERFACE IMPORTED)\n'
                'set_target_properties(GTest::' + component + ' PROPERTIES\n'
                '  INTERFACE_INCLUDE_DIRECTORIES "${_test_gtest_include_dir}"\n'
                '  INTERFACE_SYSTEM_INCLUDE_DIRECTORIES "${_test_gtest_include_dir}")\n'
                for component in components))
            (re2_prefix / 're2Config.cmake').write_text('add_library(re2::re2 INTERFACE IMPORTED)\n')
            (effcee_prefix / 'effceeConfig.cmake').write_text(
                '' if fault == 'missing-effcee-target' else 'add_library(effcee::effcee INTERFACE IMPORTED)\n')
            body = 'cmake_minimum_required(VERSION 3.22.1)\nproject(selection LANGUAGES NONE)\n' \
                   'option(SPIRV_SKIP_TESTS "test input" OFF)\nset(BUILD_SHARED_LIBS OFF)\n' \
                   'set(_test_gtest_include_dir [==[' + str(include_dir) + ']==])\n' \
                   'set(CMAKE_CXX_COMPILER_ID GNU)\n' \
                   'set(_test_expect_gtest_system_option ' + ('OFF' if fault == 'implicit-mismatch' else 'ON') + ')\n' \
                   'set(CMAKE_CXX_IMPLICIT_INCLUDE_DIRECTORIES [==[' + \
                   str(include_dir / 'different' if fault == 'implicit-mismatch' else include_dir) + ']==])\n'
            child = external
            if fault == 'child-scope':
                child = fragment + child
            else:
                body += fragment
            if fault == 'alias-property':
                child = child.replace('if (TARGET gmock AND NOT SPIRV_USE_INSTALLED_GTEST)', 'if (TARGET gmock)')
            body += 'add_subdirectory(external)\nadd_subdirectory(test)\n'
            (fixture / 'CMakeLists.txt').write_text(body)
            (fixture / 'external/CMakeLists.txt').write_text(child)
            (fixture / 'test/CMakeLists.txt').write_text(test)
            vendor = 'if(SPIRV_USE_INSTALLED_GTEST)\nmessage(FATAL_ERROR "vendor used in installed mode")\nendif()\n'
            vendor += ''.join('add_library(' + component + ' INTERFACE)\n' for component in COMPONENTS)
            vendor += 'file(WRITE "${CMAKE_BINARY_DIR}/vendor-metadata" "present")\n'
            (fixture / 'external/googletest/CMakeLists.txt').write_text(vendor)
            (fixture / 'external/effcee').mkdir()
            vendor = 'if(SPIRV_USE_INSTALLED_EFFCEE)\nmessage(FATAL_ERROR "vendor Effcee used in installed mode")\nendif()\n'
            vendor += 'add_library(effcee INTERFACE)\nadd_library(re2 INTERFACE)\n'
            vendor += 'file(WRITE "${CMAKE_BINARY_DIR}/effcee-vendor-metadata" "present")\n'
            (fixture / 'external/effcee/CMakeLists.txt').write_text(vendor)
            build = fixture / 'build'
            command = [str(args.cmake), '-S', str(fixture), '-B', str(build),
                       '-DSPIRV_SKIP_TESTS=' + ('ON' if skip else 'OFF'),
                       '-DGTest_DIR=' + str(prefix if fault != 'missing-provider' else work / 'isolated/missing'),
                       '-Deffcee_DIR=' + str(effcee_prefix), '-Dre2_DIR=' + str(re2_prefix),
                       '-DCMAKE_FIND_ROOT_PATH=' + str(work / 'isolated'), '-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY']
            if installed is not None:
                command += ['-DSPIRV_USE_INSTALLED_GTEST=' + ('ON' if installed and fault != 'effcee-only' else 'OFF'),
                            '-DSPIRV_USE_INSTALLED_EFFCEE=' + ('ON' if installed else 'OFF')]
            if fault == 'missing-provider':
                (prefix / 'GTestConfig.cmake').unlink()
            if fault == 'missing-effcee-provider':
                (effcee_prefix / 'effceeConfig.cmake').unlink()
            if fault == 'missing-re2-provider':
                (re2_prefix / 're2Config.cmake').unlink()
            result = subprocess.run(command, capture_output=True, text=True)
            output = result.stdout + result.stderr
            require((result.returncode == 0) == valid and (not error or error in output), name + ': ' + output)
            if valid:
                require((build / 'unit-metadata').is_file(), 'Unit-test selection did not reach the sibling directory')
                require((build / 'vendor-metadata').is_file() != (installed is True), 'Wrong provider path was used')
                require((build / 'effcee-vendor-metadata').is_file() != (installed is True), 'Wrong Effcee provider path')
                cache = (build / 'CMakeCache.txt').read_text()
                if installed is None:
                    require('SPIRV_USE_INSTALLED_GTEST:BOOL=OFF' in cache, 'The upstream default changed')
                    require('SPIRV_USE_INSTALLED_EFFCEE:BOOL=OFF' in cache, 'The upstream Effcee default changed')
                require('CMAKE_C_COMPILER:' not in cache and 'CMAKE_CXX_COMPILER:' not in cache,
                        'The metadata fixture selected a compiler')
            print('PASS: ' + name)

        configure('installed-root-scope', True)
        configure('system-include-causal', True, fault='implicit-mismatch')
        configure('missing-provider', True, fault='missing-provider', valid=False, error='GTest')
        configure('missing-gmock', True, components=('gtest', 'gtest_main', 'gmock_main'),
                  valid=False, error='Installed GoogleTest lacks GTest::gmock')
        configure('skip-is-rejected', True, skip=True, valid=False, error='requires SPIRV_SKIP_TESTS=OFF')
        configure('upstream-vendor-fallback', None)
        configure('child-scope-causal', True, fault='child-scope', valid=False, error='sibling test cannot see')
        configure('alias-property-causal', True, fault='alias-property', valid=False, error='ALIAS target')
        configure('missing-effcee-provider', True, fault='missing-effcee-provider', valid=False, error='effcee')
        configure('missing-effcee-target', True, fault='missing-effcee-target', valid=False,
                  error='must provide re2::re2 and effcee::effcee')
        configure('missing-re2-provider', True, fault='missing-re2-provider', valid=False, error='re2')
        configure('effcee-skip-refusal', True, fault='effcee-only', skip=True, valid=False,
                  error='SPIRV_USE_INSTALLED_EFFCEE requires SPIRV_SKIP_TESTS=OFF')
        print('PASS: twelve actual-fragment configure checks; no compiler or build invocation')
    finally:
        print(subprocess.check_output(['df', '-k', str(work)], text=True), end='')
        shutil.rmtree(work); require(not work.exists(), 'Own CMake fixture remains')
        print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True), end='')
        print('Removed owned fixture: ' + str(work))


if __name__ == '__main__':
    main()
