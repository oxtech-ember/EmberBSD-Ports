#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check selected native binutils in the real common CMake metadata paths."""
import argparse
import json
import re
from pathlib import Path
import shlex
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pkgsrc/lang/llvm/files'))
from sdk_source import load_sdk
sdk, arguments = load_sdk()
from emberbsd_sdk.stream import capture_streamed

PAIRS = {'AR': 'AR', 'RANLIB': 'RANLIB', 'NM': 'NM', 'STRIP': 'STRIP', 'LINKER': 'LD'}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'makeconf', 'bmake', 'patch', 'cmake-source', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    args = cli.parse_args(arguments)
    work = args.work.absolute()
    work.mkdir()
    tree = work / 'pkgsrc'
    (tree / 'devel').mkdir(parents=True)
    for entry in args.pkgsrc.iterdir():
        if entry.name == 'mk':
            shutil.copytree(entry, tree / 'mk')
        elif entry.name != 'devel':
            (tree / entry.name).symlink_to(entry.resolve())
    for entry in (args.pkgsrc / 'devel').iterdir():
        if entry.name == 'cmake':
            shutil.copytree(entry, tree / 'devel/cmake')
        else:
            (tree / 'devel' / entry.name).symlink_to(entry.resolve())
    commands = []
    def run(name, command):
        argv = [str(value) for value in command]
        result = capture_streamed(argv, timeout=30, stdout_limit=4 * 1024 * 1024)
        (work / (name + '.stdout')).write_bytes(result.value)
        (work / (name + '.stderr')).write_bytes(result.stderr)
        commands.append(dict(case=name, argv=argv))
        (work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        return result.value.decode()
    # Replay all infrastructure hunks for these owners in actual export order.
    targets = {'devel/cmake/Makefile', 'devel/cmake/configure-settings.mk',
               'mk/configure/cmake.mk', 'mk/compiler.mk', 'mk/cwrappers.mk'}
    replay = work / 'export-order'
    for target in targets:
        path = replay / target
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'upstream/pkgsrc' / target, path)
    for number, row in enumerate((ROOT / 'pkgsrc/export.conf').read_text().splitlines()):
        fields = row.split('\t')
        if fields[0] != 'patch':
            continue
        lines = (ROOT / fields[1]).read_text().splitlines(keepends=True)
        selected = []
        for index, line in enumerate(lines):
            if not line.startswith('--- a/') or line.split()[1][2:] not in targets:
                continue
            end = next((offset for offset in range(index + 1, len(lines))
                        if lines[offset].startswith('--- a/')), len(lines))
            selected.extend(lines[index:end])
        if selected:
            patch = work / ('export-order-' + str(number) + '.patch')
            patch.write_text(''.join(selected))
            run('export-order-' + str(number), [args.patch, '-f', '-N', '-F', '0',
                                                '-p1', '-d', replay, '-i', patch])
    source = (args.cmake_source / 'Modules/CMakeFindBinUtils.cmake').read_text()
    assert 'list(APPEND _CMAKE_TOOL_VARS AR RANLIB STRIP LINKER NM ' in source
    assert 'find_program(CMAKE_${_CMAKE_TOOL}' in source
    bootstrap_source = (args.cmake_source / 'bootstrap').read_text()
    assert 'InitialCacheFlags.cmake' in bootstrap_source
    assert re.search(r'"\$\{cmake_bootstrap_dir\}/cmake"[^\n]+"\$@"', bootstrap_source)
    # Replay the production delta over a private copy of the real framework.
    delta = ROOT / 'profiles/common-build-tools/patches/pkgsrc-cmake-binutils.patch'
    if delta.exists():
        run('framework-patch', [args.patch, '-f', '-N', '-F', '0', '-p1', '-d', tree, '-i', delta])
        shutil.copyfile(ROOT / 'profiles/common-build-tools/cmake-binutils.mk',
                        tree / 'mk/configure/ember-cmake-binutils.mk')
    for target in targets:
        assert (replay / target).read_bytes() == (tree / target).read_bytes(), target
    tools = work / "selected'tools"
    tools.mkdir()
    for name in PAIRS.values():
        path = tools / name.lower()
        path.write_text('#!/bin/sh\nexit 97\n')
        path.chmod(0o755)
    nonexec = tools / 'nonexec'
    nonexec.write_text('Labelled non-executable metadata fixture.\n')
    conf = work / 'mk.conf'
    conf.write_text('.include "' + str(args.makeconf.resolve()) + '"\n' +
        '\n'.join(name + '= ' + str(tools / name.lower()) for name in PAIRS.values()) + '\n')
    for kind in ('modern', 'legacy'):
        recipe = tree / 'devel' / ('cmake-tools-' + kind)
        recipe.mkdir()
        recipe.joinpath('PLIST').write_text('share/metadata-fixture\n')
        recipe.joinpath('Makefile').write_text('DISTNAME= cmake-tools-fixture-1.0\nCATEGORIES= devel\n'
            'MAINTAINER= pkgsrc-users@NetBSD.org\nCOMMENT= Labelled metadata fixture\nLICENSE= 2-clause-bsd\n'
            'USE_LANGUAGES= c c++\n' +
            ('.include "../../devel/cmake/build.mk"\n' if kind == 'modern' else 'USE_CMAKE= yes\n') +
            '.include "../../mk/bsd.pkg.mk"\n')
    def query(name, package, variable, extra=()):
        return run(name, [args.bmake, '-C', tree / package, 'MAKECONF=' + str(conf),
            'WRKOBJDIR=' + str(work / 'objects'), 'PKG_DBDIR=' + str(work / 'pkgdb'),
            'PKG_BUILD_OPTIONS.libxml2=', 'PKG_BUILD_OPTIONS.libarchive=', *extra, '-v', variable])
    def check_tools(text, bindir, wrappers):
        values = shlex.split(text)
        for key, source in PAIRS.items():
            matches = [arg.split('=', 1)[1] for arg in values if arg.startswith('-DCMAKE_' + key + ':FILEPATH=')]
            wrapped = source == 'LD' or (wrappers == 'no' and source in ('AR', 'RANLIB'))
            expected = str(Path(bindir.strip()) / source.lower()) if wrapped else str(tools / source.lower())
            assert matches == [expected], (key, matches, expected)
        return values
    for wrappers in ('yes', 'no'):
        mode = ['USE_CWRAPPERS=' + wrappers]
        for kind in ('modern', 'legacy'):
            package = 'devel/cmake-tools-' + kind
            label = kind + '-wrappers-' + wrappers
            # Legacy roles change only after pkgsrc's dependency barrier.
            # Create that metadata marker inside this fixture's work directory.
            if wrappers == 'no':
                cookie = Path(query(label + '-barrier', package, '_COOKIE.barrier', mode).strip())
                cookie.parent.mkdir(parents=True, exist_ok=True)
                cookie.touch()
            bindir = query(label + '-bindir', package, 'WRAPPER_BINDIR', mode)
            check_tools(query(label, package, 'CMAKE_CONFIGURE_ARGS', mode), bindir, wrappers)
            assert not query(label + '-reasons', package, 'PKG_FAIL_REASON', mode).strip()
            for variable in ('AR', 'RANLIB', 'NM', 'STRIP', 'LD', 'PKG_AR', 'PKG_RANLIB',
                             'PKG_NM', 'PKG_STRIP', 'PKG_LD', 'CWRAPPERS_WRAPPEE.ld'):
                value = query(label + '-evaluated-' + variable, package, variable, mode).strip()
                if variable.startswith('PKG_'):
                    assert value == str(tools / variable[4:].lower()), (variable, value)
                elif variable == 'CWRAPPERS_WRAPPEE.ld' and wrappers == 'yes':
                    assert value == str(tools / 'ld'), value
                elif variable in ('AR', 'RANLIB', 'LD') and wrappers == 'no':
                    assert value == variable.lower(), (variable, value)
            for key, source in PAIRS.items():
                for suffix, value in [('missing', ''), ('relative', source.lower()),
                                      ('absent', str(tools / 'absent')), ('nonexec', str(nonexec))]:
                    reason = query(label + '-' + key + '-' + suffix, package, 'PKG_FAIL_REASON',
                                   [*mode, source + '=' + value])
                    assert source in reason and 'CMake' in reason, reason
        bindir = query('bootstrap-' + wrappers + '-bindir', 'devel/cmake', 'WRAPPER_BINDIR', mode)
        bootstrap = check_tools(query('bootstrap-' + wrappers, 'devel/cmake', 'CONFIGURE_ARGS', mode),
                                bindir, wrappers)
        assert bootstrap.count('--') == 1, bootstrap
        split = bootstrap.index('--')
        assert all(bootstrap.index(arg) > split for arg in bootstrap if arg.startswith('-DCMAKE_')), bootstrap
    # Exercise native platform and cross guards without a recursive target graph.
    recipe = (tree / 'devel/cmake/Makefile').read_text()
    begin = recipe.index('# Bootstrap forwards cache definitions')
    end = recipe.index('# Origin: EmberBSD', begin)
    guard = recipe[begin:end]
    for host in ('Darwin', 'Linux', 'NetBSD'):
        for cross in ('no', 'yes'):
            fragment = work / ('guard-' + host + '-' + cross + '.mk')
            fragment.write_text('OPSYS= ' + host + '\nUSE_CROSS_COMPILE= ' + cross +
                '\n_USE_CWRAPPERS= yes\nWRAPPER_BINDIR= ' + str(work / 'generated-wrappers') +
                '\nCONFIGURE_ARGS= --existing-bootstrap-option\n' +
                '\n'.join('PKG_' + name + '= ' + str(tools / name.lower()) for name in PAIRS.values()) +
                '\n.include "' + str(tree / 'mk/configure/ember-cmake-binutils.mk') + '"\n' + guard)
            values = shlex.split(run('guard-' + host + '-' + cross,
                [args.bmake, '-f', fragment, '-v', 'CONFIGURE_ARGS']))
            if cross == 'yes':
                assert values == ['--existing-bootstrap-option'], values
            else:
                assert values.count('--') == 1, values
                assert len([value for value in values if value.startswith('-DCMAKE_')]) == 5, values
    print('PASS: pinned CMake source accepts all five cache names and forwards bootstrap argv')
    print('PASS: all affected infrastructure hunks replay in export order with zero fuzz')
    print('PASS: Darwin/Linux/NetBSD native option guards add one separator; cross guards add no flags')
    print('PASS: modern/legacy native metadata forwards five quoted selected tools and refuses invalid inputs')
    print('PASS: bootstrap forwards the same tools after one -- separator')
    print('SCOPE: metadata/source only; no compiler, CMake configure, package build or prefix writer ran')


if __name__ == '__main__':
    main()
