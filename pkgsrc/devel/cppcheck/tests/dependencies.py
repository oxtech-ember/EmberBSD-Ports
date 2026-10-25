#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Replay provider and consumer sources, then reject bundled dependency regressions."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'pkgsrc/lang/llvm/files'))
from sdk_source import load_sdk
_, arguments = load_sdk()
from emberbsd_sdk.stream import capture_streamed

parser = argparse.ArgumentParser(description=__doc__)
for name in ('archives', 'patch', 'work'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args(arguments)
a.work.mkdir()
inputs = (
    ('devel/simplecpp', 'simplecpp-1.9.1.tar.gz', 'simplecpp-1.9.1',
     'd26e36a8a6462d1655e03d67a95f5cd0228bffb1873c9349b971093494a0df59'),
    ('devel/picojson', 'picojson-111c9be5188f7350c2eac9ddaedd8cca3d7bf394.tar.gz',
     'picojson-111c9be5188f7350c2eac9ddaedd8cca3d7bf394',
     '671f89832a17e9e71398f80c0a326afa2ebe81f4c26d5a9992e1fcd0888ae151'),
    ('devel/cppcheck', 'cppcheck-2.22.0.tar.gz', 'cppcheck-2.22.0',
     'd74945deb2d50393430e07596b766f8a779512c7f60dac2a30ea64e059ece57b'),
    ('security/zoneminder', 'ZoneMinder-1.38.4.tar.gz', 'zoneminder-1.38.4', None),
)
records, sources, before = [], {}, {}
for package, filename, directory, sha256 in inputs:
    recipe = ROOT / 'pkgsrc' / package
    archive = a.archives / filename
    data = archive.read_bytes()
    info = (recipe / 'distinfo').read_text()
    actual_sha256 = hashlib.sha256(data).hexdigest()
    if sha256:
        assert actual_sha256 == sha256, filename
    for label, digest in (('BLAKE2s', hashlib.blake2s(data).hexdigest()),
                          ('SHA512', hashlib.sha512(data).hexdigest())):
        assert f'{label} ({filename}) = {digest}' in info, (filename, label)
    assert f'Size ({filename}) = {len(data)} bytes' in info, filename
    work = a.work / package.replace('/', '-')
    work.mkdir()
    with tarfile.open(archive) as stream:
        stream.extractall(work, filter='data')
    source = work / directory
    sources[package] = source
    if package == 'devel/simplecpp':
        before[package] = {name: (source / name).read_bytes() for name in
                           ('simplecpp.cpp', 'simplecpp.h', 'main.cpp', 'test.cpp',
                            'integration_test.py', 'run-tests.py', 'testutils.py', 'LICENSE')}
    if package == 'devel/picojson':
        before[package] = {name: (source / name).read_bytes() for name in
                           ('picojson.h', 'test.cc', 'picotest/picotest.c', 'picotest/picotest.h', 'LICENSE')}
    patches = sorted((recipe / 'patches').glob('patch-*'))
    for patch in patches:
        clean = b''.join(line for line in patch.read_bytes().splitlines(keepends=True)
                         if b'$NetBSD' not in line)
        assert f'SHA1 ({patch.name}) = {hashlib.sha1(clean).hexdigest()}' in info, patch
        result = capture_streamed([str(a.patch), '-f', '-N', '-F', '0', '-p0',
                                   '-d', str(source), '-i', str(patch)],
                                  timeout=30, stdout_limit=1024*1024)
        (work / (patch.name + '.stdout')).write_bytes(result.value)
        (work / (patch.name + '.stderr')).write_bytes(result.stderr)
    records.append({'package': package, 'archive': filename, 'sha256': actual_sha256,
                    'patch_count': len(patches)})

simple, pico = sources['devel/simplecpp'], sources['devel/picojson']
cpp, zone = sources['devel/cppcheck'], sources['security/zoneminder']
for package, files in before.items():
    for name, data in files.items():
        assert (sources[package] / name).read_bytes() == data, (package, name)
for name in ('simplecpp.cpp', 'simplecpp.h'):
    assert (simple / name).read_bytes() == (cpp / 'externals/simplecpp' / name).read_bytes(), name
assert (pico / 'picojson.h').read_bytes() == (cpp / 'externals/picojson/picojson.h').read_bytes()
assert (pico / 'picojson.h').read_bytes() == (zone / 'dep/jwt-cpp/include/picojson/picojson.h').read_bytes()


def check_consumers():
    top = (cpp / 'CMakeLists.txt').read_text()
    assert 'find_package(simplecpp 1.9.1 EXACT CONFIG REQUIRED)' in top
    assert 'find_package(picojson 1.3.0.20210117 CONFIG REQUIRED)' in top
    for provider in ('simplecpp', 'picojson'):
        assert f'add_subdirectory(externals/{provider})' not in top
        assert f'add_library({provider} ALIAS {provider}::{provider})' in top
        assert f'devel/{provider}/buildlink3.mk' in (ROOT / 'pkgsrc/devel/cppcheck/Makefile').read_text()
    jwt = (zone / 'dep/jwt-cpp/CMakeLists.txt').read_text()
    assert 'find_package(picojson 1.3.0 REQUIRED)' in jwt
    assert 'picojson::picojson>' not in jwt
    assert 'target_link_libraries(jwt-cpp INTERFACE picojson::picojson)' in jwt
    for name in ('jwt.h', 'traits/kazuho-picojson/traits.h'):
        content = (zone / 'dep/jwt-cpp/include/jwt-cpp' / name).read_text()
        assert '#include <picojson.h>' in content
        assert '#include "picojson/picojson.h"' not in content
    recipe = (ROOT / 'pkgsrc/security/zoneminder/Makefile').read_text()
    assert '-DJWT_EXTERNAL_PICOJSON:BOOL=ON' in recipe
    assert 'devel/picojson/buildlink3.mk' in recipe


check_consumers()
# The complete existing ZoneMinder recipe is retained outside this dependency edge.
for old in (ROOT / 'upstream/pkgsrc/security/zoneminder').rglob('*'):
    if old.is_file() and old.name not in ('Makefile', 'distinfo'):
        relative = old.relative_to(ROOT / 'upstream/pkgsrc/security/zoneminder')
        expected = old.read_bytes()
        if str(relative) == 'files/README-pkgsrc.md':
            expected = expected.replace(b'\n \n', b'\n\n')
        assert expected == (ROOT / 'pkgsrc/security/zoneminder' / relative).read_bytes(), relative
simple_cmake = (simple / 'CMakeLists.txt').read_text()
for text in ('add_library(simplecpp_lib simplecpp.cpp)', 'EXPORT_NAME simplecpp',
             'SOVERSION 1.9', 'target_compile_features(simplecpp_lib PUBLIC cxx_std_11)',
             'SIMPLECPP_EXPORT INTERFACE SIMPLECPP_IMPORT',
             'target_link_libraries(testrunner PRIVATE simplecpp::simplecpp)',
             'add_test(NAME testrunner COMMAND testrunner)', 'COMPATIBILITY ExactVersion'):
    assert text in simple_cmake, text
pico_cmake = (pico / 'CMakeLists.txt').read_text()
for text in ('add_library(picojson INTERFACE)', 'NAMESPACE picojson::',
             'foreach(name test-core test-core-int64)', 'test.cc picotest/picotest.c',
             'target_compile_definitions(test-core-int64 PRIVATE PICOJSON_USE_INT64)',
             'COMPATIBILITY SameMajorVersion ARCH_INDEPENDENT'):
    assert text in pico_cmake, text
assert not any(word in simple_cmake + pico_cmake for word in ('FetchContent', 'ExternalProject_Add'))
# Cause a bundling regression in the disposable prepared tree, then restore it.
fault_file = cpp / 'CMakeLists.txt'
original = fault_file.read_bytes()
try:
    fault_file.write_bytes(original + b'\nadd_subdirectory(externals/simplecpp)\n')
    try:
        check_consumers()
    except AssertionError:
        pass
    else:
        raise AssertionError('bundled provider regression was accepted')
finally:
    fault_file.write_bytes(original)
check_consumers()
(a.work / 'result.json').write_text(json.dumps({
    'sources': records, 'source_identity': 'provider implementations match both bundled consumers',
    'negative_control': 'reintroduced bundled SimpleCpp rejected',
    'scope': 'source and package interfaces only; no compiler or executable tests'}, indent=2) + '\n')
print('PASS: four pinned source inputs and zero-fuzz patch replay')
print('PASS: unchanged provider implementations, shared consumer imports and bundled-provider refusal')
print('PREPARED: complete upstream CMake unit suites; execution remains pending')
