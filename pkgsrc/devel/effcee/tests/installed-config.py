#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check actual Effcee dependency and export fragments without a compiler."""
import argparse
import hashlib
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tarfile
import tempfile


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cmake', 'archive', 'patch', 'work-parent'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    require(all(p.is_absolute() for p in vars(args).values()), 'Use absolute paths')
    recipe = Path(__file__).resolve().parents[1]
    distinfo = (recipe / 'distinfo').read_text()
    for label, algorithm in (('BLAKE2s', 'blake2s'), ('SHA512', 'sha512')):
        expected = re.search(r'^' + label + r' \(effcee-1\.2026\.0.tar.gz\) = (\w+)$', distinfo, re.M)[1]
        require(hashlib.new(algorithm, args.archive.read_bytes()).hexdigest() == expected, 'Archive hash mismatch')
    patch = recipe / 'patches/patch-installed-dependencies'
    patch_sha1 = runpy.run_path(str(recipe.parents[2] / 'scripts/prepare-pkgsrc.py'))['patch_sha1']
    require(patch_sha1(patch) == re.search(
        r'^SHA1 \(patch-installed-dependencies\) = (\w+)$', distinfo, re.M)[1], 'Patch hash mismatch')
    print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True), end='')
    work = Path(tempfile.mkdtemp(prefix='effcee-installed-config-', dir=args.work_parent))
    try:
        source = work / 'source'
        with tarfile.open(args.archive) as archive:
            for name in ('CMakeLists.txt', 'effcee/CMakeLists.txt'):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.extractfile('effcee-f8e8a164822d4f65e757bff66bc00e1567959aa0/' + name).read())
        (source / 'cmake').mkdir()
        result = subprocess.run([str(args.patch), '-F', '0', '-p0', '-i', str(patch)],
                                cwd=source, capture_output=True, text=True)
        require(result.returncode == 0 and not re.search(r'fuzz|offset', result.stdout, re.I), result.stdout + result.stderr)
        root = (source / 'CMakeLists.txt').read_text()
        fragment = root[root.index('option(EFFCEE_USE_INSTALLED_DEPS'):root.index('add_subdirectory(effcee)')]
        library = (source / 'effcee/CMakeLists.txt').read_text()
        export = library[library.index('install(TARGETS effcee'):library.index('if(EFFCEE_BUILD_TESTING)')]
        prefix = work / 'providers/lib/cmake'
        for name in ('absl', 're2', 'GTest'):
            (prefix / name).mkdir(parents=True)
        (prefix / 'absl/abslConfig.cmake').write_text('add_library(absl::base INTERFACE IMPORTED)\n')
        re2_config = prefix / 're2/re2Config.cmake'
        re2_config.write_text('if(NOT TARGET re2::re2)\nadd_library(re2::re2 INTERFACE IMPORTED)\nendif()\n')
        gtest = prefix / 'GTest/GTestConfig.cmake'
        gtest.write_text(''.join('add_library(GTest::' + n + ' INTERFACE IMPORTED)\n'
                                for n in ('gtest', 'gtest_main', 'gmock', 'gmock_main')))
        (prefix / 'GTest/GTestConfigVersion.cmake').write_text(
            'set(PACKAGE_VERSION 1.18.0)\nset(PACKAGE_VERSION_COMPATIBLE TRUE)\n')
        # An INTERFACE stand-in permits real export/install/config execution with
        # LANGUAGES NONE. This does not qualify the C++ library or its ELF ABI.
        (source / 'CMakeLists.txt').write_text(
            'cmake_minimum_required(VERSION 3.22.1)\nproject(effcee VERSION 1.2026.0 LANGUAGES NONE)\n'
            'set(EFFCEE_BUILD_TESTING ON)\nset(CMAKE_INSTALL_LIBDIR lib)\n' + fragment +
            'add_library(effcee INTERFACE)\ntarget_link_libraries(effcee INTERFACE re2)\nadd_subdirectory(effcee)\n')
        (source / 'effcee/CMakeLists.txt').write_text(export)

        def configure(name, src, extra=(), valid=True, error=''):
            build = work / ('build-' + name)
            result = subprocess.run([str(args.cmake), '-S', str(src), '-B', str(build),
                '-DCMAKE_FIND_ROOT_PATH=' + str(work / 'providers'),
                '-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY', *extra], capture_output=True, text=True)
            output = result.stdout + result.stderr
            require((result.returncode == 0) == valid and (not error or error in output), name + ': ' + output)
            if valid:
                cache = (build / 'CMakeCache.txt').read_text()
                require('CMAKE_C_COMPILER:' not in cache and 'CMAKE_CXX_COMPILER:' not in cache, 'Compiler selected')
            print('PASS: ' + name)
            return build

        build = configure('installed-export', source, ('-DEFFCEE_USE_INSTALLED_DEPS=ON',
                          '-DCMAKE_INSTALL_PREFIX=' + str(work / 'installed')))
        subprocess.run([str(args.cmake), '--install', str(build)], check=True, capture_output=True)
        moved = work / 'relocated'
        (work / 'installed').rename(moved)
        consumer = work / 'consumer'
        consumer.mkdir()
        (consumer / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.22.1)\n'
            'project(consumer LANGUAGES NONE)\nfind_package(effcee 1.2026.0 CONFIG REQUIRED)\n'
            'if(NOT TARGET effcee::effcee OR NOT TARGET re2::re2)\nmessage(FATAL_ERROR "Missing exported targets")\nendif()\n'
            'get_target_property(deps effcee::effcee INTERFACE_LINK_LIBRARIES)\n'
            'if(NOT deps STREQUAL "re2::re2")\nmessage(FATAL_ERROR "Missing exported RE2 dependency")\nendif()\n')
        location = ('-Deffcee_DIR=' + str(moved / 'lib/cmake/effcee'),)
        configure('relocated-consumer', consumer, location)
        re2_config.unlink()
        configure('missing-re2-consumer', consumer, location, False, 're2')
        configure('missing-re2-build', source, ('-DEFFCEE_USE_INSTALLED_DEPS=ON',), False, 're2')
        re2_config.write_text('add_library(re2::re2 INTERFACE IMPORTED)\n')
        gtest.write_text('add_library(GTest::gtest INTERFACE IMPORTED)\n')
        configure('missing-gmock-build', source, ('-DEFFCEE_USE_INSTALLED_DEPS=ON',), False, 'GoogleTest')
        print('PASS: five actual-fragment checks; no compiler or C++ build')
    finally:
        print(subprocess.check_output(['df', '-k', str(work)], text=True), end='')
        shutil.rmtree(work)
        require(not work.exists(), 'Own fixture remains')
        print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True), end='')
        print('Removed owned fixture: ' + str(work))


if __name__ == '__main__':
    main()
