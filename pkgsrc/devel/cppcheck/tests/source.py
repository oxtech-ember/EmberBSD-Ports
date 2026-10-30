#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the shared recipe and exact patch replay; do not compile an analyzer."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'pkgsrc/lang/llvm/files'))
from sdk_source import load_sdk
_, arguments = load_sdk()
from emberbsd_sdk.stream import capture_streamed
cli = argparse.ArgumentParser(description=__doc__)
for name in ('archive', 'patch', 'work', 'cmake'):
    cli.add_argument('--' + name, type=Path, required=True)
a = cli.parse_args(arguments)
p = ROOT / 'pkgsrc/devel/cppcheck'
a.work.mkdir()
data = a.archive.read_bytes()
assert hashlib.sha256(data).hexdigest() == 'd74945deb2d50393430e07596b766f8a779512c7f60dac2a30ea64e059ece57b', 'changed upstream archive'
info = (p / 'distinfo').read_text()
for label, value in [('BLAKE2s', hashlib.blake2s(data).hexdigest()), ('SHA512', hashlib.sha512(data).hexdigest())]:
    assert label + ' (' + a.archive.name + ') = ' + value in info, label
assert 'Size (' + a.archive.name + ') = ' + str(len(data)) + ' bytes' in info
with tarfile.open(a.archive) as archive:
    archive.extractall(a.work / 'source', filter='data')
s = a.work / 'source/cppcheck-2.22.0'
original_compileroptions = (s / 'cmake/compileroptions.cmake').read_bytes()
token = (s / 'lib/token.cpp').read_bytes()
for patch in sorted((p / 'patches').glob('patch-*')):
    clean = b''.join(line for line in patch.read_bytes().splitlines(keepends=True) if b'$NetBSD' not in line)
    assert 'SHA1 (' + patch.name + ') = ' + hashlib.sha1(clean).hexdigest() in info, patch.name
    result = capture_streamed([str(a.patch), '-f', '-N', '-F', '0', '-p0', '-d', str(s), '-i', str(patch)], timeout=30, stdout_limit=1024*1024)
    (a.work / (patch.name + '.stdout')).write_bytes(result.value)
    (a.work / (patch.name + '.stderr')).write_bytes(result.stderr)

original_module = a.work / 'compileroptions.cmake.original'
original_module.write_bytes(original_compileroptions)
abi_test = capture_streamed([
    sys.executable, str(p / 'tests/compileroptions_abi.py'),
    '--cmake', str(a.cmake),
    '--fixture', str(p / 'tests/compileroptions-abi'),
    '--patched-module', str(s / 'cmake/compileroptions.cmake'),
    '--original-module', str(original_module),
    '--work', str(a.work / 'compileroptions-abi'),
], timeout=30, stdout_limit=1024*1024)
(a.work / 'compileroptions-abi.stdout').write_bytes(abi_test.value)
(a.work / 'compileroptions-abi.stderr').write_bytes(abi_test.stderr)
recipe, options = (p / 'Makefile').read_text(), (p / 'options.mk').read_text()
assert re.search(r'^DISTNAME=\s*cppcheck-2\.22\.0$', recipe, re.M)
for flag in ('BUILD_CLI:BOOL=ON', 'BUILD_TESTING:BOOL=ON', 'HAVE_RULES:BOOL=ON', 'USE_BUNDLED_TINYXML2:BOOL=OFF', 'BUILD_MANPAGE:BOOL=ON', 'DISABLE_DMAKE:BOOL=ON', 'CMAKE_MACOSX_BUNDLE:BOOL=OFF'):
    assert '-D' + flag in recipe, flag
for field in ('devel/pcre2/buildlink3.mk', 'devel/simplecpp/buildlink3.mk', 'devel/picojson/buildlink3.mk', 'textproc/tinyxml2/buildlink3.mk', 'devel/boost-headers/buildlink3.mk', 'Python_EXECUTABLE:FILEPATH=${TOOL_PYTHONBIN}', 'PKG_CONFIG_EXECUTABLE:FILEPATH=${TOOLS_CMD.pkg-config}', 'LIBXML2_XMLLINT_EXECUTABLE:FILEPATH=${TOOLBASE}/bin/xmllint', 'XSLTPROC:FILEPATH=${TOOLBASE}/bin/xsltproc', 'DB2MAN:FILEPATH=${TOOLBASE}/share/xsl/docbook/manpages/docbook.xsl'):
    assert field in recipe, field
assert 'USE_Z3' not in recipe and 'math/z3' not in recipe
assert 'qt5:qt6' in options and 'devel/qt6-qttools/buildlink3.mk' in options
assert 'x11/qt6-qtbase/host-tools.mk' in options and 'EMBERBSD_QT_HOST_PATH' not in options
assert (s / 'lib/token.cpp').read_bytes() == token and b'Token::astStringZ3()' in token
regex = (s / 'lib/regex.cpp').read_text()
assert '#include "regex.h"' in regex and regex.index('#include "regex.h"') < regex.index('class PcreRegex')
for symbol in ('PCRE2_CODE_UNIT_WIDTH 8', 'pcre2_compile', 'pcre2_match_data_create_from_pattern', 'pcre2_match_data_free', 'pcre2_next_match', 'Engine::Pcre'):
    assert symbol in regex, symbol
assert '#include <pcre.h>' not in regex and '#define PCRE2_STATIC' not in regex
top = (s / 'CMakeLists.txt').read_text()
assert 'find_package(simplecpp 1.9.1 EXACT CONFIG REQUIRED)' in top
assert 'find_package(picojson 1.3.0.20210117 CONFIG REQUIRED)' in top
assert 'add_subdirectory(externals/simplecpp)' not in top
assert 'add_subdirectory(externals/picojson)' not in top
finder = (s / 'cmake/findDependencies.cmake').read_text()
for field in ('IMPORTED_TARGET libpcre2-8>=10.47', 'PkgConfig::PCRE2', 'find_package(boost_headers CONFIG REQUIRED)', 'Boost::headers', 'boost_headers_FOUND'):
    assert field in finder, field
assert 'find_package(Boost' not in finder
assert 'PCRE2_CONFIG ?= pcre2-config' in (s / 'Makefile').read_text()
assert 'PCRE2_CONFIG ?= pcre2-config' in (s / 'tools/dmake/dmake.cpp').read_text()
assert 'EXCLUDE_FROM_ALL' in (s / 'tools/dmake/CMakeLists.txt').read_text()
assert 'WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}' in (s / 'tools/dmake/CMakeLists.txt').read_text()
unit = (s / 'test/testregex.cpp').read_text()
for case in ('emptyMatch', 'emptySubject', 'lookAround', 'manyCaptures', 'utfEmptyMatch', 'matchError', 'callbackException'):
    assert 'TEST_CASE(' + case + ')' in unit, case
expected = {'bin/cppcheck', 'bin/cppcheck-htmlreport', 'man/man1/cppcheck.1'}
for directory, patterns in [('addons', ('*.py','*.json')), ('cfg', ('*.cfg',)), ('platforms', ('*.xml',))]:
    for pattern in patterns:
        expected.update('share/cppcheck/' + directory + '/' + f.name for f in (s / directory).glob(pattern))
expected.add('${PLIST.qt6}bin/cppcheck-gui')
expected.update('${PLIST.qt6}bin/' + f.stem + '.qm' for f in (s / 'gui').glob('*.ts'))
expected.update('${PLIST.qt6}' + f for f in ('share/applications/cppcheck-gui.desktop','share/icons/hicolor/64x64/apps/cppcheck-gui.png','share/icons/hicolor/scalable/apps/cppcheck-gui.svg'))
actual = {line for line in (p / 'PLIST').read_text().splitlines() if line and not line.startswith('@')}
assert actual == expected, (sorted(expected-actual), sorted(actual-expected))
assert 'devel/cppcheck' in (ROOT / 'pkgsrc/replaces').read_text().splitlines()
(a.work / 'result.json').write_text(json.dumps({'version':'2.22.0','install_paths':len(actual),'source_patches':len(list((p/'patches').glob('patch-*'))),'runtime_cases_prepared':7,'scope':'source/metadata only; compilation, analyzer execution, static and memory checks pending'}, indent=2)+'\n')
print('PASS: current common recipe, checksums, zero-fuzz source replay and complete install roster')
print('PASS: rules/PCRE2/shared XML/GUI/report/man/test metadata; AST format API retained')
print('PREPARED: seven regex runtime cases; none compiled or executed')
