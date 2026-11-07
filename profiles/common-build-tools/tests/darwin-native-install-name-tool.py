#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the native MAKECONF tool profile.
"""Publish the selected llvm-install-name-tool as install_name_tool.

usage: darwin-native-install-name-tool.py BMAKE NEW_WORK

A native build's MAKECONF includes EMBERBSD-COMMON-TOOLS-MK.CONF, which
includes the generated host-tools.mk. That include selects
llvm-install-name-tool and creates ar, nm and ranlib. It does not create
install_name_tool. The native profile must, and a cross include of the
same generated file must not.

The selected mksh has no printf builtin (pkgsrc/shells/mksh). The included
profile replaces PATH with the host prefix path, so that directory must
contain the external printf. /usr/bin:/bin is not the recipe PATH.
"""
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import types
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'pkgsrc/lang/llvm/files'))
from sdk_source import load_sdk

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / 'profiles/common-build-tools'
ADAPTER = PROFILE / 'cross/prepare-native-tools.py'


def require(value, message):
    if not value:
        raise AssertionError(message)


def load_adapter():
    spec = importlib.util.spec_from_file_location('native_make_adapter', ADAPTER)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    return adapter


def external_printf():
    # mksh executes printf from PATH. A shell builtin is not that utility.
    for candidate in (Path('/usr/bin/printf'), Path('/bin/printf')):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise AssertionError('the host has no external printf utility')


def toolset(adapter, root, host):
    tools = {role: str(root / ('sdk-' + role))
             for role in (*adapter.ROLE_VARIABLES, *adapter.ROLE_DIRECTORIES, *adapter.OPTIONAL_ROLES, 'fetch')}
    flags = {'cppflags': (), 'cflags': (), 'cxxflags': (), 'ldflags': ()}
    path = root / 'bin'
    path.mkdir(parents=True)
    printf = path / 'printf'
    printf.symlink_to(external_printf())
    return types.SimpleNamespace(
        tool=lambda role: tools[role], tools=tools, path=str(path),
        abi_flags=flags, compiler_family='clang', host={'os': host},
        command=lambda role: (tools[role], '-c', '-x', 'assembler') if role == 'as' else (tools[role],))


def render(adapter, selected, prefix, services):
    bindir = prefix / 'bin'
    bindir.mkdir(parents=True)
    for _role, _variable, name in adapter.DARWIN_HOST_TOOLS:
        path = bindir / name
        path.write_text('#!/bin/sh\nexec ' + str(external_printf()) + ' \'%s\\n\' "$0" "$@"\n')
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    with mock.patch.object(adapter, 'DARWIN_SYSTEM_SERVICES', services):
        extra = adapter.darwin_host_tools(str(prefix), selected) if selected.host['os'] == 'Darwin' else ()
    return adapter.render(selected, qt=extra)


def evaluate(bmake, work, host_tools, opsys, cross):
    profile = work / 'export'
    profile.mkdir(parents=True)
    shutil.copyfile(PROFILE / 'mk.conf', profile / 'EMBERBSD-COMMON-TOOLS-MK.CONF')
    shutil.copyfile(PROFILE / 'cross/native-tools.mk', profile / 'EMBERBSD-NATIVE-TOOLS.MK')
    shutil.copyfile(ROOT / 'pkgsrc/defaults.mk.conf', profile / 'EMBERBSD-DEFAULTS-MK.CONF')
    shutil.copyfile(ROOT / 'pkgsrc/versions.mk', profile / 'EMBERBSD-VERSIONS.MK')
    prefix = work / 'prefix'
    lines = [
        'BSD_PKG_MK= yes',
        f'OPSYS= {opsys}',
        f'USE_CROSS_COMPILE= {"yes" if cross else "no"}',
        f'PREFIX= {prefix}',
        f'LOCALBASE= {prefix}',
        f'EMBERBSD_SDK_SOURCE= {work}/sdk',
        f'EMBERBSD_HOST_PREFIX= {prefix}',
        'EMBERBSD_HOST_COMPILER_FAMILY= clang',
        'EMBERBSD_HOST_FETCH_MODE= fetch',
        f'EMBERBSD_NATIVE_TOOLSET_MAKECONF= {host_tools}',
        'EMBERBSD_NATIVE_TOOLSET_VERIFIED= ${EMBERBSD_SDK_SOURCE}|${EMBERBSD_HOST_PREFIX}|${EMBERBSD_HOST_COMPILER_FAMILY}|${EMBERBSD_HOST_FETCH_MODE}|${EMBERBSD_NATIVE_TOOLSET_MAKECONF}|${EMBERBSD_NATIVE_CXX_BINDING_RECORD:U}|${EMBERBSD_NATIVE_CXX_STAGE_ROOT:U}',
        f'.include "{profile}/EMBERBSD-COMMON-TOOLS-MK.CONF"',
        'all:',
        '\t@printf \'%s\\n\' ${TOOLS_CREATE:Q}',
        '\t@printf \'%s\\n\' ${TOOLS_PATH.install_name_tool:Q}',
        '\t@printf \'%s\\n\' ${TOOLS_SCRIPT.install_name_tool:Q}',
        '\t@printf \'%s\\n\' ${EMBERBSD_DARWIN_INSTALL_NAME_TOOL:Q}',
    ]
    makefile = work / 'aarch64.mk.conf'
    makefile.write_text('\n'.join(lines) + '\n')
    # The include replaces PATH. Keep the external printf on the initial path
    # too: bmake may run the selected shell before that assignment.
    exported = None
    for line in host_tools.read_bytes().splitlines():
        if line.startswith(b'PATH:= '):
            exported = line.split(b' ', 1)[1].decode()
    require(exported, 'the included profile does not assign PATH')
    utility = Path(exported) / 'printf'
    require(utility.is_symlink() and os.access(utility, os.X_OK),
            f'the included profile PATH has no external printf: {exported!r}')
    environment = os.environ.copy()
    environment['PATH'] = exported + os.pathsep + '/usr/bin:/bin'
    return subprocess.run([bmake, '-f', str(makefile), 'all'], cwd=work,
                          capture_output=True, text=True, env=environment)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    load_sdk([])
    bmake, work = sys.argv[1], Path(sys.argv[2])
    require(Path(bmake).is_absolute() and work.is_absolute() and not work.exists(),
            'use an absolute bmake and a new absolute work directory')
    work.mkdir()
    adapter = load_adapter()
    prefix = work / 'host-prefix'
    codesign = work / 'codesign'
    codesign.write_text('#!/bin/sh\n')
    codesign.chmod(0o755)
    services = (('codesign', 'EMBERBSD_DARWIN_TOOL.codesign', str(codesign)),)
    darwin = toolset(adapter, work / 'roles', 'Darwin')
    generated = render(adapter, darwin, prefix, services)
    require(b'TOOLS_CREATE+= install_name_tool' not in generated,
            'the generated host include already creates install_name_tool')
    require(b'.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"\nTOOLS_CREATE+= ar\n' in generated,
            'the generated host include no longer creates ar only for native builds')
    selected = prefix / 'bin/llvm-install-name-tool'
    require(f'EMBERBSD_DARWIN_INSTALL_NAME_TOOL?= {selected}'.encode() in generated
            or f'.if "${{EMBERBSD_DARWIN_INSTALL_NAME_TOOL}}" != "{selected}"'.encode() in generated,
            'the generated host include does not select llvm-install-name-tool')
    require(f'PATH:= {darwin.path}\n'.encode() in generated,
            'the included profile does not export the fixture prefix path')
    # mksh runs printf by PATH lookup. This is that lookup, with no shell builtin.
    external = subprocess.run(['printf', '%s\n', 'external-printf'],
                              capture_output=True, text=True, env={'PATH': darwin.path})
    require(external.returncode == 0 and external.stdout == 'external-printf\n',
            f'external printf did not run from the profile PATH: {external.stderr}')
    host_tools = work / 'config/host-tools.mk'
    host_tools.parent.mkdir()
    host_tools.write_bytes(generated)
    native = evaluate(bmake, work / 'native', host_tools, 'Darwin', False)
    require(native.returncode == 0, native.stderr.strip() or native.stdout)
    created, path, script, variable = native.stdout.splitlines()
    require(created.split().count('install_name_tool') == 1, created)
    for name in ('ar', 'nm', 'ranlib'):
        require(created.split().count(name) == 1, created)
    require(path == variable == str(selected), f'{path!r} {variable!r}')
    require(script == f'exec {selected} "$@"', script)
    tools = work / 'tools/bin'
    tools.mkdir(parents=True)
    wrapper = tools / 'install_name_tool'
    wrapper.write_text('#!/bin/sh\n' + script + '\n')
    wrapper.chmod(0o755)
    found = subprocess.run(
        ['install_name_tool', '-id', '@rpath/libgettextlib-1.0.dylib',
         './.libs/libgettextlib-1.0.dylib'],
        cwd=work, capture_output=True, text=True, env={'PATH': str(tools)})
    require(found.returncode == 0, found.stderr)
    require(found.stdout.splitlines() == [
        str(selected), '-id', '@rpath/libgettextlib-1.0.dylib',
        './.libs/libgettextlib-1.0.dylib'], found.stdout)
    (work / 'empty').mkdir()
    hidden = subprocess.run(['/bin/sh', '-c', 'install_name_tool -id @rpath/x x'], cwd=work,
                            capture_output=True, text=True, env={'PATH': str(work / 'empty')})
    require(hidden.returncode == 127, f'bare command exited {hidden.returncode}')
    alone_env = os.environ.copy()
    alone_env.update(PATH=darwin.path + os.pathsep + '/usr/bin:/bin',
                     USE_CROSS_COMPILE='no', OPSYS='Darwin')
    alone = subprocess.run([bmake, '-f', str(host_tools), '-V', '${TOOLS_CREATE}'],
                           cwd=work, capture_output=True, text=True, env=alone_env)
    require(alone.returncode == 0 and 'install_name_tool' not in alone.stdout.split(),
            f'generated include leaked install_name_tool: {alone.stdout} {alone.stderr}')
    netbsd_tools = work / 'config/netbsd-host-tools.mk'
    netbsd_tools.write_bytes(render(adapter, toolset(adapter, work / 'netbsd-roles', 'NetBSD'),
                                    work / 'netbsd-prefix', services))
    kept = evaluate(bmake, work / 'netbsd', netbsd_tools, 'NetBSD', False)
    require(kept.returncode == 0 and 'install_name_tool' not in kept.stdout.splitlines()[0].split(),
            f'NetBSD native profile created install_name_tool: {kept.stdout} {kept.stderr}')
    missing = evaluate(bmake, work / 'missing', netbsd_tools, 'Darwin', False)
    require(missing.returncode != 0 and 'did not publish install_name_tool' in missing.stderr,
            f'Darwin accepted a host include without the tool: {missing.returncode} {missing.stderr}')
    crossed = evaluate(bmake, work / 'cross', host_tools, 'Darwin', True)
    require(crossed.returncode != 0 and 'requires native package builds' in crossed.stderr,
            f'cross build used the native profile: {crossed.stderr}')
    require('TOOLS_CREATE+= install_name_tool' not in (PROFILE / 'cross/mk.conf').read_text(),
            'the cross profile creates install_name_tool')
    recipe = (PROFILE / 'patches/gettext-external-recipe.patch').read_text()
    require('--enable-relocatable' in recipe, 'relocatable gettext-tools was removed')
    print('PASS: native MAKECONF publishes the selected llvm-install-name-tool')


if __name__ == '__main__':
    main()
