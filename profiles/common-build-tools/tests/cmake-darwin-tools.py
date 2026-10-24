#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check explicit Darwin CMake tools without a compiler or shared prefix."""
import argparse
import json
import re
from pathlib import Path
import shlex
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pkgsrc/lang/llvm/files'))
from sdk_source import load_sdk
sdk, arguments = load_sdk()
from emberbsd_sdk.stream import capture_streamed

ROLES = {'INSTALL_NAME_TOOL': 'EMBERBSD_DARWIN_INSTALL_NAME_TOOL',
         'TAPI': 'EMBERBSD_DARWIN_TAPI'}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('bmake', 'patch', 'pkgsrc', 'cmake-source', 'llvm-tapi-options', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    args = cli.parse_args(arguments)
    work = args.work.absolute()
    work.mkdir()
    tools = work / "selected tools'"
    tools.mkdir()
    selected = {}
    for key in ('AR', 'RANLIB', 'NM', 'STRIP', 'LD', *ROLES):
        path = tools / key.lower()
        path.write_text('#!/bin/sh\nexit 97\n')
        path.chmod(0o755)
        selected[key] = path
    nonexec = tools / 'nonexec'
    nonexec.write_text('Labelled non-executable metadata fixture.\n')
    sdk = work / "selected SDK's"
    sdk.mkdir()
    commands = []
    def query(label, host='Darwin', cross='no', overrides=None, wrappers='yes'):
        values = {'PKG_' + key: str(selected[key]) for key in ('AR', 'RANLIB', 'NM', 'STRIP', 'LD')}
        values.update({value: str(selected[key]) for key, value in ROLES.items()})
        values['EMBERBSD_DARWIN_TAPI_KIND'] = 'apple'
        values['OSX_SDK_PATH'] = str(sdk)
        values.update(overrides or {})
        fragment = work / (label + '.mk')
        fragment.write_text('OPSYS= ' + host + '\nUSE_CROSS_COMPILE= ' + cross +
            '\n_USE_CWRAPPERS= ' + wrappers + '\nWRAPPER_BINDIR= ' + str(work / 'generated-wrappers') + '\n' +
            '\n'.join(key + '= ' + value for key, value in values.items()) +
            '\n.include "' + str(ROOT / 'profiles/common-build-tools/cmake-binutils.mk') + '"\n')
        argv = [str(args.bmake), '-f', str(fragment), '-v', '_EMBERBSD_CMAKE_BINUTILS_ARGS',
                '-v', 'PKG_FAIL_REASON']
        result = capture_streamed(argv, timeout=15, stdout_limit=1024 * 1024)
        (work / (label + '.stdout')).write_bytes(result.value)
        (work / (label + '.stderr')).write_bytes(result.stderr)
        commands.append(dict(case=label, argv=argv))
        (work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        lines = result.value.decode().splitlines()
        return shlex.split(lines[0]), '\n'.join(lines[1:])
    values, reason = query('native-selected')
    assert not reason.strip(), reason
    for key in ROLES:
        assert values.count('-DCMAKE_' + key + ':FILEPATH=' + str(selected[key])) == 1, (key, values)
    assert '-DEMBERBSD_DARWIN_TAPI_KIND:STRING=apple' in values, values
    assert '-DEMBERBSD_CMAKE_NATIVE_TOOLS:BOOL=ON' in values, values
    assert '-DCMAKE_POLICY_DEFAULT_CMP0137:STRING=NEW' in values, values
    assert values.count('-DCMAKE_OSX_SYSROOT:PATH=' + str(sdk)) == 1, values
    assert not any(value.startswith('-DCMAKE_OSX_DEPLOYMENT_TARGET:') for value in values), values
    for key, selector in ROLES.items():
        for label, value in [('missing', ''), ('relative', key.lower()), ('absent', str(tools / 'absent')),
                             ('nonexec', str(nonexec)), ('directory', str(tools))]:
            values, reason = query(key + '-' + label, overrides={selector: value})
            assert selector in reason and 'CMake' in reason, reason
            assert not any(value.startswith('-DCMAKE_' + key + ':FILEPATH=') for value in values), values
    for label, value in [('missing', ''), ('relative', 'MacOSX.sdk'),
                         ('absent', str(work / 'absent-sdk')), ('file', str(selected['LD']))]:
        values, reason = query('sysroot-' + label, overrides={'OSX_SDK_PATH': value})
        assert 'OSX_SDK_PATH' in reason and 'CMake' in reason, reason
        assert not any(value.startswith('-DCMAKE_OSX_SYSROOT:') for value in values), values
    for host, cross in [('Linux', 'no'), ('NetBSD', 'no'), ('Darwin', 'yes')]:
        absent = {value: '' for value in ROLES.values()}
        absent['OSX_SDK_PATH'] = ''
        values, reason = query(host + '-' + cross, host, cross, absent)
        assert not reason.strip(), reason
        assert not any(value.startswith('-DCMAKE_' + key + ':') for value in values for key in ROLES), values
        assert not any(value.startswith('-DEMBERBSD_DARWIN_TAPI_KIND:') for value in values), values
        assert not any(value.startswith('-DCMAKE_OSX_SYSROOT:') for value in values), values
        assert ('-DEMBERBSD_CMAKE_NATIVE_TOOLS:BOOL=ON' in values) == (cross == 'no'), values
        assert ('-DCMAKE_POLICY_DEFAULT_CMP0137:STRING=NEW' in values) == (cross == 'no'), values
    for kind in ('apple', 'llvm-readtapi'):
        values, reason = query('kind-' + kind, overrides={'EMBERBSD_DARWIN_TAPI_KIND': kind})
        assert not reason.strip(), reason
        assert '-DEMBERBSD_DARWIN_TAPI_KIND:STRING=' + kind in values, values
    for index, kind in enumerate(('', 'unknown', 'apple llvm-readtapi', 'apple;unexpected')):
        values, reason = query('invalid-kind-' + str(index), overrides={'EMBERBSD_DARWIN_TAPI_KIND': kind})
        assert 'EMBERBSD_DARWIN_TAPI_KIND' in reason and 'CMake' in reason, reason
        assert not any(value.startswith('-DEMBERBSD_DARWIN_TAPI_KIND:') for value in values), values
    values, reason = query('legacy-wrapper-paths', wrappers='no')
    assert not reason.strip(), reason
    for key, alias in [('AR', 'ar'), ('RANLIB', 'ranlib'), ('LINKER', 'ld')]:
        assert '-DCMAKE_' + key + ':FILEPATH=' + str(work / 'generated-wrappers' / alias) in values, values
    source = work / 'source'
    (source / 'Modules/Platform').mkdir(parents=True)
    darwin = source / 'Modules/Platform/Darwin.cmake'
    original = (args.cmake_source / 'Modules/Platform/Darwin.cmake').read_bytes()
    assert b'<CMAKE_TAPI> --stubify' not in original
    assert b'EMBERBSD_DARWIN_TAPI_KIND' not in original
    darwin.write_bytes(original)
    (source / 'Modules/CMakeFindBinUtils.cmake').write_bytes(
        (args.cmake_source / 'Modules/CMakeFindBinUtils.cmake').read_bytes())
    for label, patch in [('existing', args.pkgsrc / 'devel/cmake/patches/patch-Modules_Platform_Darwin.cmake'),
                         ('new', ROOT / 'profiles/common-build-tools/patches/cmake-darwin-tapi-kind.patch')]:
        result = capture_streamed([str(args.patch), '-f', '-N', '-F', '0', '-p0', '-d', str(source),
                                   '-i', str(patch)], timeout=15, stdout_limit=1024 * 1024)
        (work / ('source-' + label + '.stdout')).write_bytes(result.value)
        (work / ('source-' + label + '.stderr')).write_bytes(result.stderr)
    policy = darwin.read_text()
    apple = '<CMAKE_TAPI> stubify -isysroot <CMAKE_OSX_SYSROOT> -o <TARGET_IMPLIB> <TARGET>'
    llvm = '<CMAKE_TAPI> --stubify -o <TARGET_IMPLIB> <TARGET>'
    assert policy.count(apple) == 2 and policy.count(llvm) == 1
    assert 'if(EMBERBSD_DARWIN_TAPI_KIND STREQUAL "llvm-readtapi")' in policy
    assert 'elseif(EMBERBSD_DARWIN_TAPI_KIND STREQUAL "apple")' in policy
    assert 'message(FATAL_ERROR "EMBERBSD_DARWIN_TAPI_KIND must be apple or llvm-readtapi")' in policy
    assert 'list(APPEND CMAKE_PLATFORM_IMPLICIT_LINK_DIRECTORIES' in policy
    finder = (source / 'Modules/CMakeFindBinUtils.cmake').read_text()
    roster = re.search(r'list\(APPEND CMAKE_TRY_COMPILE_PLATFORM_VARIABLES(.*?)\)', finder, re.S)
    assert roster, finder
    names = roster.group(1).split()
    required = {'CMAKE_AR', 'CMAKE_RANLIB', 'CMAKE_NM', 'CMAKE_STRIP', 'CMAKE_LINKER',
                'CMAKE_TAPI', 'CMAKE_INSTALL_NAME_TOOL', 'EMBERBSD_DARWIN_TAPI_KIND',
                'CMAKE_TRY_COMPILE_PLATFORM_VARIABLES', 'EMBERBSD_CMAKE_NATIVE_TOOLS',
                'CMAKE_POLICY_DEFAULT_CMP0137'}
    assert required <= set(names), names
    # APPEND preserves a package's existing roster. Deduplication keeps order.
    assert 'set(CMAKE_TRY_COMPILE_PLATFORM_VARIABLES' not in finder
    assert 'list(REMOVE_DUPLICATES CMAKE_TRY_COMPILE_PLATFORM_VARIABLES)' in finder
    assert 'if(EMBERBSD_CMAKE_NATIVE_TOOLS)' in finder
    assert 'if(CMAKE_TRY_COMPILE_NO_PLATFORM_VARIABLES)' in finder
    assert 'message(FATAL_ERROR "Explicit native tools require try_compile platform variables")' in finder
    core = (args.cmake_source / 'Source/cmCoreTryCompile.cxx').read_text()
    begin = core.index('// Forward a set of variables to the inner project cache.')
    end = core.index('if (!this->SrcFileSignature &&', begin)
    forwarding = core[begin:end]
    assert 'this->SrcFileSignature ||' in forwarding
    assert re.search(r'GetPolicyStatus\(cmPolicies::CMP0137\) ==\s*cmPolicies::NEW', forwarding)
    assert '!this->Makefile->IsOn("CMAKE_TRY_COMPILE_NO_PLATFORM_VARIABLES")' in forwarding
    assert 'vars.insert(varList.begin(), varList.end())' in forwarding
    assert 'this->Makefile->GetDefinition(var)' in forwarding
    assert 'arguments.CMakeFlags.emplace_back(std::move(flag))' in forwarding
    assert 'if(APPLE AND "TAPI" IN_LIST _CMAKE_TOOL_VARS AND NOT CMAKE_TAPI)' in finder
    assert 'find_program(CMAKE_INSTALL_NAME_TOOL NAMES ' in finder
    initialize = (args.cmake_source / 'Modules/Platform/Darwin-Initialize.cmake').read_text()
    assert 'if(CMAKE_OSX_SYSROOT)' in initialize
    assert 'set(_CMAKE_OSX_SYSROOT_DEFAULT "${CMAKE_OSX_SYSROOT}")' in initialize
    assert 'if(NOT IS_DIRECTORY "${CMAKE_OSX_SYSROOT}")' in initialize
    assert 'if(NOT CMAKE_OSX_SYSROOT)' in initialize
    assert 'COMMAND xcrun ${_sdk_macosx} --show-sdk-path' in initialize
    assert 'vars.insert(kCMAKE_OSX_SYSROOT)' in forwarding
    bootstrap = (args.cmake_source / 'bootstrap').read_text()
    assert re.search(r'"\$\{cmake_bootstrap_dir\}/cmake"[^\n]+InitialCacheFlags\.cmake[^\n]+"\$@"', bootstrap)
    options = args.llvm_tapi_options.read_text()
    assert 'Flag<["-", "--"], name>' in options and 'def stubify: FF<"stubify"' in options
    assert 'defm output: JS<"o"' in options and 'isysroot' not in options
    print('PASS: legacy archive/linker wrappers retain their absolute generated paths')
    print('PASS: existing and new Darwin source patches replay with zero fuzz')
    print('PASS: source/project try_compile uses the appended roster and retains package variables')
    print('PASS: deep propagation includes the roster, marker, policy default and selected tools')
    print('PASS: finite rules preserve Apple argv and use supported llvm-readtapi options')
    print('PASS: explicit Darwin SDK path forwards once and refuses four invalid inputs')
    print('PASS: pinned initialization/bootstrap/try_compile preserve the selected sysroot')
    print('PASS: native Darwin forwards both quoted explicit tools and refuses ten invalid inputs')
    print('PASS: finite TAPI kind accepts apple/llvm-readtapi and refuses four invalid inputs')
    print('PASS: Linux, NetBSD and cross metadata add no Darwin tool requirement')
    print('SCOPE: source and metadata only; no CMake configure, compiler, tool execution or prefix writer ran')


if __name__ == '__main__':
    main()
