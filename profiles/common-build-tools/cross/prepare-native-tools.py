#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Map one qualified SDK selection to a pinned pkgsrc native include."""
import argparse
import hashlib
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
    lines = ['# Generated from a qualified SDK native toolset. Do not edit.']
    for role, variable in ROLE_VARIABLES.items():
        value = literal(toolset.tool(role))
        if "'" in value:
            from emberbsd_sdk.errors import SDKError
            raise SDKError('The native make mapping does not support quotes in tool paths')
        pinned = '_EMBER_SDK_' + role.upper().replace('-', '_')
        lines += [pinned + ':= ' + value,
                  '.if "${' + pinned + '}" != "' + value + '"',
                  '.error ' + pinned + ' differs from the qualified SDK tool', '.endif',
                  variable + '?= ${' + pinned + '}',
                  '.if "${' + variable + '}" != "' + value + '"',
                  '.error ' + variable + ' differs from the qualified SDK tool', '.endif']
    flags = toolset.abi_flags
    for role, name, arguments in (
            ('cc', 'CC', flags['cppflags'] + flags['cflags'] + flags['ldflags']),
            ('cxx', 'CXX', flags['cppflags'] + flags['cxxflags'] + flags['ldflags']),
            ('cpp', 'CPP', flags['cppflags'])):
        pinned = '_EMBER_NATIVE_' + name + '_COMMAND'
        value = literal(shlex.join([toolset.tool(role), *arguments]))
        lines += [pinned + ':= ' + value,
                  '.if "${' + pinned + '}" != "' + value + '"',
                  '.error ' + pinned + ' differs from the qualified native ABI command', '.endif']
    for name in ('cppflags', 'cflags', 'cxxflags', 'ldflags'):
        value = literal(shlex.join(toolset.abi_flags[name]))
        pinned = '_EMBER_SDK_' + name.upper()
        lines += [pinned + ':= ' + value,
                  '.if "${' + pinned + '}" != "' + value + '"',
                  '.error ' + pinned + ' differs from the qualified native ABI flags', '.endif']
        for prefix in ('NATIVE_', 'HOST_'):
            variable = prefix + name.upper()
            lines += [variable + '?= ${' + pinned + '}',
                      '.if "${' + variable + '}" != "' + value + '"',
                      '.error ' + variable + ' differs from the qualified native ABI flags', '.endif']
    for role, variable in (('cc', 'HOST_CC'), ('cxx', 'HOST_CXX'), ('cpp', 'HOST_CPP')):
        pinned = '_EMBER_SDK_' + role.upper()
        value = literal(toolset.tool(role))
        lines += [variable + '?= ${' + pinned + '}',
                  '.if "${' + variable + '}" != "' + value + '"',
                  '.error ' + variable + ' differs from the qualified SDK compiler', '.endif']
    return ('\n'.join(lines) + '\n').encode()


def selection(arguments):
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.native_toolset import NATIVE_TOOLSET_API, load_native_toolset
    if type(NATIVE_TOOLSET_API) is not int or NATIVE_TOOLSET_API != 1:
        raise SDKError('SDK native toolset API 1 is required')
    toolset = load_native_toolset(
        arguments.descriptor, descriptor_sha256=arguments.descriptor_sha256,
        accepted_producer_receipt={'path': arguments.producer_receipt,
                                   'sha256': arguments.producer_receipt_sha256},
        required_roles=tuple(ROLE_VARIABLES))
    if Path(sys.executable).resolve(strict=True) != Path(toolset.tool('python')).resolve(strict=True):
        raise SDKError('The adapter interpreter differs from the qualified SDK Python')
    return toolset


def publish(toolset, destination):
    from emberbsd_sdk import paths
    from emberbsd_sdk.publication import (DIRECTORY_PUBLICATION_API,
                                         publish_directory_noreplace)
    from emberbsd_sdk.errors import SDKError
    if type(DIRECTORY_PUBLICATION_API) is not int or DIRECTORY_PUBLICATION_API != 1:
        raise SDKError('SDK directory publication API 1 is required')
    if not Path(destination).is_absolute():
        raise SDKError('Use an absolute native include destination')
    output = Path(paths.canonical_new(destination))
    if os.path.lexists(output):
        raise SDKError('The native include destination must be new')
    data = render(toolset)
    # The staging directory and destination have one owned parent. Native
    # no-replace publication preserves a concurrent destination entry.
    with tempfile.TemporaryDirectory(prefix='.native-tools-', dir=output.parent) as temporary:
        stage = Path(temporary)
        (stage / 'host-tools.mk').write_bytes(data)
        (stage / 'selection.json').write_text(json.dumps(toolset.as_dict(), indent=2) + '\n')
        for path in stage.iterdir():
            path.chmod(0o444)
        publish_directory_noreplace(str(stage), str(output))
    return {'makeconf': str(output / 'host-tools.mk'),
            'makeconf_sha256': hashlib.sha256(data).hexdigest()}


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('publish', 'verify'))
    parser.add_argument('--descriptor', required=True)
    parser.add_argument('--descriptor-sha256', required=True)
    parser.add_argument('--producer-receipt', required=True)
    parser.add_argument('--producer-receipt-sha256', required=True)
    parser.add_argument('--output')
    parser.add_argument('--makeconf')
    parser.add_argument('--makeconf-sha256')
    args = parser.parse_args(arguments)
    if args.operation == 'publish':
        if not args.output or args.makeconf or args.makeconf_sha256:
            parser.error('publish requires only --output')
    elif not args.makeconf or not args.makeconf_sha256 or args.output:
        parser.error('verify requires only --makeconf and --makeconf-sha256')
    toolset = selection(args)
    if args.operation == 'publish':
        print(json.dumps(publish(toolset, args.output)))
        return
    from emberbsd_sdk import paths
    from emberbsd_sdk.errors import SDKError
    if not Path(args.makeconf).is_absolute():
        raise SDKError('Use an absolute native include path')
    path = Path(paths.canonical_existing(args.makeconf))
    paths.regular_file(str(path))
    data = path.read_bytes()
    if path.stat().st_mode & 0o222 or hashlib.sha256(data).hexdigest() != args.makeconf_sha256 or data != render(toolset):
        raise SDKError('The native include differs from the pinned qualified SDK mapping')
    print('VERIFIED')


if __name__ == '__main__':
    loader = sdk_loader()
    loader.install_signal_handlers()
    try:
        _, arguments = loader.load_sdk()
        main(arguments)
    except Exception as error:
        loader.exit_error(error)
