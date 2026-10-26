#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check real recipe metadata for explicit native Darwin archive selection."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
if len(sys.argv) not in (5, 6):
    raise SystemExit('Use EXPORTED_PKGSRC MAKECONF BMAKE NEW_WORK [BOOTSTRAP_MAKECONF]')
export, makeconf, bmake = map(lambda value: Path(value).resolve(strict=True), sys.argv[1:4])
bootstrap_makeconf = Path(sys.argv[5]).resolve(strict=True) if len(sys.argv) == 6 else None
work = Path(sys.argv[4]).absolute()
work.mkdir()
root = Path(__file__).resolve().parents[3]
tree = work / 'pkgsrc'
(tree / 'lang').mkdir(parents=True)
for entry in export.iterdir():
    if entry.name != 'lang':
        (tree / entry.name).symlink_to(entry)
for entry in (export / 'lang').iterdir():
    if entry.name in ('llvm', 'clang', 'compiler-rt'):
        shutil.copytree(root / 'pkgsrc/lang' / entry.name, tree / 'lang' / entry.name)
    else:
        (tree / 'lang' / entry.name).symlink_to(entry)
# The chosen executable is not an accepted SDK tool. No producer must execute it.
selected = work / 'llvm-libtool-darwin'
selected.write_text('#!/bin/sh\n: > ' + shlex.quote(str(work / 'tool-executed')) + '\nexit 99\n')
selected.chmod(0o755)
nonexec = work / 'non-executable'
nonexec.write_text('Labelled non-executable selection fixture.\n')
rows = []
fields = ('OPSYS', 'USE_CROSS_COMPILE', 'PKG_LD', 'EMBERBSD_DARWIN_LD64_LLD',
          'PKG_FAIL_REASON', 'CMAKE_CONFIGURE_ARGS')


def query(package, name, selectors=(), *, configuration=makeconf):
    # Keep unrelated libxml2 option discovery out of this isolated metadata query.
    command = [str(bmake), '-C', str(tree / 'lang' / package),
               'MAKECONF=' + str(configuration), 'WRKOBJDIR=' + str(work / 'objects'),
               'PKG_DBDIR=' + str(work / 'pkgdb'), 'PKG_BUILD_OPTIONS.libxml2=',
               'EMBERBSD_DARWIN_TOOL_PHASE=full', *selectors]
    for field in fields:
        command.extend(('-v', field))
    result = subprocess.run(command, capture_output=True, text=True)
    (work / (package + '-' + name + '.log')).write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    values = result.stdout.splitlines()
    assert len(values) == len(fields), result.stdout
    row = dict(zip(fields, values))
    rows.append(dict(package=package, case=name, argv=command, values=row))
    (work / 'receipt.json').write_text(json.dumps(rows, indent=2) + '\n')
    return row


# The real initial configuration binds LD, not the later compiler.mk PKG_LD
# snapshot. A fixture that supplies PKG_LD early hides recipe include-order bugs.
if bootstrap_makeconf is not None:
    for package in ('llvm', 'clang', 'compiler-rt'):
        bootstrap = query(package, 'bootstrap-selected-linker', [
            'EMBERBSD_DARWIN_BOOTSTRAP=yes', 'EMBERBSD_DARWIN_TOOL_PHASE=initial'],
            configuration=bootstrap_makeconf)
        assert not bootstrap['PKG_FAIL_REASON'], bootstrap
        assert bootstrap['PKG_LD'] == bootstrap['EMBERBSD_DARWIN_LD64_LLD'], bootstrap
        selected_linkers = [arg.split('=', 1)[1]
                            for arg in shlex.split(bootstrap['CMAKE_CONFIGURE_ARGS'])
                            if arg.startswith('-DLD64_EXECUTABLE:')]
        assert selected_linkers and set(selected_linkers) == {bootstrap['PKG_LD']}, bootstrap


for package in ('llvm', 'clang'):
    native = query(package, 'selected', ['EMBERBSD_DARWIN_LIBTOOL=' + str(selected)])
    assert native['OPSYS'] == 'Darwin' and native['USE_CROSS_COMPILE'].lower() != 'yes', native
    assert not native['PKG_FAIL_REASON'], native
    options = shlex.split(native['CMAKE_CONFIGURE_ARGS'])
    libtool = [arg.split('=', 1)[1] for arg in options if arg.startswith('-DCMAKE_LIBTOOL')]
    assert libtool and set(libtool) == {str(selected)}, 'Selected Darwin archive tool was not forwarded: ' + str(libtool)
    ld64 = [arg.split('=', 1)[1] for arg in options if arg.startswith('-DLD64_EXECUTABLE:')]
    dsymutil = [arg.split('=', 1)[1] for arg in options if arg.startswith('-DCMAKE_DSYMUTIL:')]
    assert ld64 and set(ld64) == {native['PKG_LD']}, 'Selected PKG_LD was not forwarded: ' + str(ld64)
    dsym = work / 'llvm-dsymutil'
    dsym.write_text('#!/bin/sh\n: > ' + shlex.quote(str(work / 'dsymutil-executed')) + '\nexit 99\n')
    dsym.chmod(0o755)
    selected_dsym = query(package, 'selected-dsymutil', [
        'EMBERBSD_DARWIN_LIBTOOL=' + str(selected), 'EMBERBSD_DARWIN_DSYMUTIL=' + str(dsym)])
    dsym_args = [arg.split('=', 1)[1] for arg in shlex.split(selected_dsym['CMAKE_CONFIGURE_ARGS'])
                 if arg.startswith('-DCMAKE_DSYMUTIL:')]
    assert dsym_args and set(dsym_args) == {str(dsym)}, 'Selected dsymutil was not forwarded: ' + str(dsym_args)
    for phase in ('initial', 'full'):
        phase_args = ['EMBERBSD_DARWIN_TOOL_PHASE=' + phase,
                      'EMBERBSD_DARWIN_DSYMUTIL=' + str(dsym)]
        if phase == 'full':
            phase_args.append('EMBERBSD_DARWIN_LIBTOOL=' + str(selected))
        phase_row = query(package, phase, phase_args)
        assert not phase_row['PKG_FAIL_REASON'], phase_row
        phase_options = shlex.split(phase_row['CMAKE_CONFIGURE_ARGS'])
        # CMake uses the last definition even when an override adds :BOOL.
        definitions = {arg[2:].split('=', 1)[0].split(':', 1)[0]: arg.split('=', 1)[1]
                       for arg in phase_options if arg.startswith('-D') and '=' in arg}
        if package == 'llvm':
            for key in ('LLVM_BUILD_LLVM_DYLIB', 'LLVM_LINK_LLVM_DYLIB'):
                assert definitions.get(key) == 'ON', (phase, key, definitions.get(key))
        if phase == 'initial':
            assert definitions['LLVM_DARWIN_ARCHIVE_TOOL'] == 'ar', phase_row
            if package == 'llvm':
                finite = query(package, 'initial-static-tools', phase_args + [
                    'LLVM_BUILD_LLVM_DYLIB=OFF', 'LLVM_LINK_LLVM_DYLIB=OFF'])
                assert not finite['PKG_FAIL_REASON'], finite
                finite_defs = {arg[2:].split('=', 1)[0].split(':', 1)[0]: arg.split('=', 1)[1]
                               for arg in shlex.split(finite['CMAKE_CONFIGURE_ARGS'])
                               if arg.startswith('-D') and '=' in arg}
                for key in ('LLVM_BUILD_LLVM_DYLIB', 'LLVM_LINK_LLVM_DYLIB'):
                    assert finite_defs.get(key) == 'OFF', (key, finite_defs.get(key))
                assert finite_defs['LLVM_DARWIN_ARCHIVE_TOOL'] == 'ar', finite
        assert any(arg.startswith('-DLD64_EXECUTABLE:') for arg in phase_options), phase_row
        assert any(arg == '-DCMAKE_DSYMUTIL:FILEPATH=' + str(dsym) for arg in phase_options), phase_row
    for name, value in [('missing', ''), ('relative', 'llvm-libtool-darwin'),
                        ('absent', str(work / 'absent')), ('nonexec', str(nonexec)),
                        ('directory', str(work))]:
        values = ['EMBERBSD_DARWIN_LIBTOOL=' + value]
        refused = query(package, name, values)
        assert 'EMBERBSD_DARWIN_LIBTOOL' in refused['PKG_FAIL_REASON'], refused
        assert '-DCMAKE_LIBTOOL' not in refused['CMAKE_CONFIGURE_ARGS'], refused
    for name, value in [('dsym-missing', ''), ('dsym-relative', 'llvm-dsymutil'),
                        ('dsym-absent', str(work / 'absent-dsymutil')),
                        ('dsym-nonexec', str(nonexec)), ('dsym-directory', str(work))]:
        refused = query(package, name, ['EMBERBSD_DARWIN_DSYMUTIL=' + value])
        assert 'EMBERBSD_DARWIN_DSYMUTIL' in refused['PKG_FAIL_REASON'], refused
        assert '-DCMAKE_DSYMUTIL' not in refused['CMAKE_CONFIGURE_ARGS'], refused
    for system in ('Linux', 'NetBSD'):
        context = ['OPSYS=' + system, 'MACHINE_ARCH=aarch64', 'HOST_MACHINE_ARCH=aarch64',
                   'OS_VERSION=' + ('7.0' if system == 'Linux' else '11.0'),
                   'OPSYS_VERSION=' + ('070000' if system == 'Linux' else '110000'),
                   'LOWER_OPSYS=' + system.lower()]
        plain = query(package, system, context)
        ignored = query(package, system + '-ignored', context + ['EMBERBSD_DARWIN_LIBTOOL=relative'])
        assert plain == ignored, 'A native non-Darwin query consumed the Darwin selector'
        assert '-DCMAKE_LIBTOOL' not in plain['CMAKE_CONFIGURE_ARGS'], plain
# Parse the actual production fragment for the cross guard. Full cross recipe
# admission needs a target sysroot; it is outside this metadata fixture.
fragment = work / 'cross-context.mk'
fragment.write_text('USE_CROSS_COMPILE= yes\nCMAKE_CONFIGURE_ARGS= -DKEEP_TARGET=ON\n'
                    'CMAKE_CONFIGURE_ARGS.Darwin= -DKEEP_DARWIN=ON\n'
                    '.include "' + str(tree / 'lang/llvm/darwin.mk') + '"\n')
for system in ('Darwin', 'NetBSD'):
    command = [str(bmake), '-f', str(fragment), 'OPSYS=' + system]
    for field in ('PKG_FAIL_REASON', 'CMAKE_CONFIGURE_ARGS', 'CMAKE_CONFIGURE_ARGS.Darwin'):
        command.extend(('-v', field))
    plain = subprocess.run(command, capture_output=True, text=True, check=True)
    ignored = subprocess.run(command + ['EMBERBSD_DARWIN_LIBTOOL=relative'],
                             capture_output=True, text=True, check=True)
    assert plain.stdout == ignored.stdout == '\n-DKEEP_TARGET=ON\n-DKEEP_DARWIN=ON\n', plain.stdout + ignored.stdout
    (work / ('cross-' + system + '.log')).write_text(plain.stdout + ignored.stdout)
assert not (work / 'tool-executed').exists(), 'Metadata admission executed the archive tool'
assert not (work / 'dsymutil-executed').exists(), 'Metadata admission executed dsymutil'
print('PASS: LLVM/Clang native Darwin linker/dsymutil selectors, both phases retain LLVM dylibs, invalid-path refusals; Linux/NetBSD metadata unchanged')
print('SCOPE: recipe metadata only; no compiler, archive tool, package phase or prefix writer ran')
