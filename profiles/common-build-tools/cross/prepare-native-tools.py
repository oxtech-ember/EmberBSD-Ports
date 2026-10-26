#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Map a native Ports prefix to pkgsrc host tool variables."""
import argparse
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile

sys.dont_write_bytecode = True

ROLE_VARIABLES = {
    'cc': 'EMBERBSD_CROSS_BUILD_CC', 'cxx': 'EMBERBSD_CROSS_BUILD_CXX',
    'cpp': 'EMBERBSD_CROSS_BUILD_CPP', 'as': 'EMBERBSD_CROSS_BUILD_AS',
    'ld': 'EMBERBSD_CROSS_BUILD_LD', 'ar': 'EMBERBSD_CROSS_BUILD_AR',
    'ranlib': 'EMBERBSD_CROSS_BUILD_RANLIB', 'nm': 'EMBERBSD_CROSS_BUILD_NM',
    'strip': 'EMBERBSD_CROSS_BUILD_STRIP', 'cmake': 'EMBERBSD_BUILD_CMAKE',
    'python': 'EMBERBSD_CROSS_BUILD_PYTHON', 'sh': 'CONFIG_SHELL',
    'meson': 'TOOLS_PLATFORM.meson', 'ninja': 'TOOLS_PLATFORM.ninja',
    'pkg-config': 'TOOLS_PLATFORM.pkg-config', 'make': 'EMBERBSD_NATIVE_MAKE',
    'bmake': 'EMBERBSD_NATIVE_BMAKE', 'gmake': 'TOOLS_PLATFORM.gmake',
    'xz': 'TOOLS_PLATFORM.xz', 'xzcat': 'TOOLS_PLATFORM.xzcat',
    'install': 'TOOLS_PLATFORM.install',
}


def sdk_loader():
    here = Path(__file__).resolve()
    candidates = [here.parent / 'lang/llvm/files/sdk_source.py']
    if len(here.parents) > 3:
        candidates.append(here.parents[3] / 'pkgsrc/lang/llvm/files/sdk_source.py')
    loader = next((path for path in candidates if path.is_file()), None)
    if loader is None:
        raise ValueError('The exported shared SDK source loader is missing')
    sys.path.insert(0, str(loader.parent))
    import sdk_source
    if Path(sdk_source.__file__).resolve() != loader:
        raise ValueError('A different SDK source loader is already imported')
    return sdk_source


def literal(value):
    from emberbsd_sdk.errors import SDKError
    if not isinstance(value, str) or any(c in value for c in '\0\r\n\\"$#'):
        raise SDKError('The native make mapping does not support control lines, backslashes, double quotes, dollar signs or hashes')
    return value


def render(toolset):
    lines = ['# Generated from the selected Ports host prefix. Do not edit.']
    family = toolset.compiler_family
    if family not in ('clang', 'gcc'):
        from emberbsd_sdk.errors import SDKError
        raise SDKError('The native compiler family must be clang or gcc')
    lines += ['EMBERBSD_HOST_COMPILER_FAMILY?= ' + family,
              '.if "${EMBERBSD_HOST_COMPILER_FAMILY}" != "' + family + '"',
              '.error The native compiler family differs from the selected prefix',
              '.endif']
    search = literal(toolset.path)
    lines += ['PATH:= ' + search, '.if "${PATH}" != "' + search + '"',
              '.error PATH differs from the selected host prefix', '.endif', '.export PATH']
    for role, variable in ROLE_VARIABLES.items():
        value = literal(shlex.join(toolset.command(role)) if role == 'as' else toolset.tool(role))
        if "'" in value:
            from emberbsd_sdk.errors import SDKError
            raise SDKError('The native make mapping does not support quotes in tool paths')
        pinned = '_EMBER_SDK_' + role.upper().replace('-', '_')
        lines += [pinned + ':= ' + value,
                  '.if "${' + pinned + '}" != "' + value + '"',
                  '.error ' + pinned + ' differs from the selected Ports tool', '.endif',
                  variable + '?= ${' + pinned + '}',
                  '.if "${' + variable + '}" != "' + value + '"',
                  '.error ' + variable + ' differs from the selected Ports tool', '.endif']
    flags = toolset.abi_flags
    for role, name, arguments in (
            ('cc', 'CC', flags['cppflags'] + flags['cflags'] + flags['ldflags']),
            ('cxx', 'CXX', flags['cppflags'] + flags['cxxflags'] + flags['ldflags']),
            ('cpp', 'CPP', flags['cppflags'])):
        pinned = '_EMBER_NATIVE_' + name + '_COMMAND'
        value = literal(shlex.join([toolset.tool(role), *arguments]))
        lines += [pinned + ':= ' + value,
                  '.if "${' + pinned + '}" != "' + value + '"',
                  '.error ' + pinned + ' differs from the selected native ABI command', '.endif']
    for name in ('cppflags', 'cflags', 'cxxflags', 'ldflags'):
        value = literal(shlex.join(toolset.abi_flags[name]))
        pinned = '_EMBER_SDK_' + name.upper()
        lines += [pinned + ':= ' + value,
                  '.if "${' + pinned + '}" != "' + value + '"',
                  '.error ' + pinned + ' differs from the selected native ABI flags', '.endif']
        for prefix in ('NATIVE_', 'HOST_'):
            variable = prefix + name.upper()
            lines += [variable + '?= ${' + pinned + '}',
                      '.if "${' + variable + '}" != "' + value + '"',
                      '.error ' + variable + ' differs from the selected native ABI flags', '.endif']
    for role, variable in (('cc', 'HOST_CC'), ('cxx', 'HOST_CXX'), ('cpp', 'HOST_CPP')):
        pinned = '_EMBER_SDK_' + role.upper()
        value = literal(toolset.tool(role))
        lines += [variable + '?= ${' + pinned + '}',
                  '.if "${' + variable + '}" != "' + value + '"',
                  '.error ' + variable + ' differs from the selected Ports compiler', '.endif']
    return ('\n'.join(lines) + '\n').encode()


def selection(arguments):
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.native_toolset import load_host_prefix
    toolset = load_host_prefix(arguments.host_prefix,
                              required_roles=tuple(ROLE_VARIABLES),
                              compiler_family=arguments.compiler_family)
    if Path(sys.executable).resolve(strict=True) != Path(toolset.tool('python')).resolve(strict=True):
        raise SDKError('The adapter interpreter differs from the selected Ports Python')
    return toolset


def write(toolset, destination):
    from emberbsd_sdk import paths
    from emberbsd_sdk.errors import SDKError
    if not Path(destination).is_absolute():
        raise SDKError('Use an absolute native include destination')
    output = Path(paths.canonical_new(destination))
    data = render(toolset)
    # Replace only the requested configuration file, after a complete write.
    with tempfile.NamedTemporaryFile(prefix='.native-tools-', dir=output.parent,
                                     delete=False) as temporary:
        stage = Path(temporary.name)
        try:
            temporary.write(data)
            temporary.close()
            os.replace(stage, output)
        finally:
            stage.unlink(missing_ok=True)
    return {'makeconf': str(output)}


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('write', 'verify'))
    parser.add_argument('--host-prefix', required=True)
    parser.add_argument('--compiler-family', choices=('clang', 'gcc'), default='clang')
    parser.add_argument('--output')
    parser.add_argument('--makeconf')
    args = parser.parse_args(arguments)
    if args.operation == 'write':
        if not args.output or args.makeconf:
            parser.error('write requires only --output')
    elif not args.makeconf or args.output:
        parser.error('verify requires only --makeconf')
    toolset = selection(args)
    if args.operation == 'write':
        print(json.dumps(write(toolset, args.output)))
        return
    from emberbsd_sdk import paths
    from emberbsd_sdk.errors import SDKError
    if not Path(args.makeconf).is_absolute():
        raise SDKError('Use an absolute native include path')
    path = Path(paths.canonical_existing(args.makeconf))
    paths.regular_file(str(path))
    data = path.read_bytes()
    if data != render(toolset):
        raise SDKError('Regenerate the native include for the selected host prefix')
    print('VERIFIED')


if __name__ == '__main__':
    loader = sdk_loader()
    loader.install_signal_handlers()
    try:
        _, arguments = loader.load_sdk()
        main(arguments)
    except Exception as error:
        loader.exit_error(error)
