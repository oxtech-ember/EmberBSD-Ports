#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Map a native Ports prefix to pkgsrc host tool variables."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
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
    'nawk': 'EMBERBSD_NATIVE_AWK',
    # Native pkgsrc recipes and BSD submakes must not select system tools.
    'gcp': 'TOOLS_PLATFORM.cp', 'gtouch': 'TOOLS_PLATFORM.touch',
    'gsed': 'TOOLS_PLATFORM.sed', 'gcat': 'TOOLS_PLATFORM.cat',
    'gmv': 'TOOLS_PLATFORM.mv', 'gchmod': 'TOOLS_PLATFORM.chmod',
    'genv': 'TOOLS_PLATFORM.env', 'ggrep': 'TOOLS_PLATFORM.grep',
    'gegrep': 'TOOLS_PLATFORM.egrep', 'gfgrep': 'TOOLS_PLATFORM.fgrep',
    'gdiff': 'TOOLS_PLATFORM.diff', 'grm': 'TOOLS_PLATFORM.rm',
    'gmkdir': 'TOOLS_PLATFORM.mkdir', 'gln': 'TOOLS_PLATFORM.ln',
    'gtr': 'TOOLS_PLATFORM.tr', 'gexpr': 'TOOLS_PLATFORM.expr',
    'gsort': 'TOOLS_PLATFORM.sort', 'ghead': 'TOOLS_PLATFORM.head',
    'gcut': 'TOOLS_PLATFORM.cut', 'gdirname': 'TOOLS_PLATFORM.dirname',
    'gbasename': 'TOOLS_PLATFORM.basename',
}
# These generators are required only by their respective consumers.
OPTIONAL_ROLES = {'clang-tblgen': 'EMBERBSD_CLANG_TABLEGEN',
                  'wayland-scanner': 'EMBERBSD_WAYLAND_SCANNER',
                  'flex': 'TOOLS_PLATFORM.flex', 'bison': 'TOOLS_PLATFORM.bison',
                  'yacc': 'TOOLS_PLATFORM.yacc', 'rpcgen': 'TOOLS_PATH.rpcgen',
                  'gcmp': 'TOOLS_PLATFORM.cmp', 'gchgrp': 'TOOLS_PLATFORM.chgrp',
                  'gchown': 'TOOLS_PLATFORM.chown', 'gwc': 'TOOLS_PLATFORM.wc',
                  'gprintf': 'TOOLS_PLATFORM.printf', 'gtail': 'TOOLS_PLATFORM.tail',
                  'gxargs': 'TOOLS_PLATFORM.xargs', 'gid': 'TOOLS_PLATFORM.id',
                  'gfind': 'TOOLS_PLATFORM.find', 'bsdtar': 'TOOLS_PLATFORM.bsdtar',
                  'zcat': 'TOOLS_PLATFORM.gzcat', 'gdate': 'TOOLS_PLATFORM.date',
                  'ghostname': 'TOOLS_PLATFORM.hostname', 'gls': 'TOOLS_PLATFORM.ls',
                  'gpwd': 'TOOLS_PLATFORM.pwd', 'grmdir': 'TOOLS_PLATFORM.rmdir',
                  'gsleep': 'TOOLS_PLATFORM.sleep', 'gtee': 'TOOLS_PLATFORM.tee'}
# These variables select the directory of the role tool.
ROLE_DIRECTORIES = {
    # Native LLVM TableGen tools for the lld and clang cross recipes.
    'llvm-tblgen': 'EMBERBSD_LLVM_NATIVE_TOOLS',
}
# Cross Qt modules take host moc, rcc, uic and lrelease from the native Qt.
# qtpaths reports these directories. Qt installs it below the prefix.
QT_QTPATHS = 'qt6/bin/qtpaths'
QT_QUERIES = {'qt-host-path': ('EMBERBSD_QT_HOST_PATH', 'QT_INSTALL_PREFIX'),
              'qt-host-libexecs': ('EMBERBSD_QT_HOST_LIBEXECS', 'QT_INSTALL_LIBEXECS')}


def qt_host_paths(prefix, search_path):
    from emberbsd_sdk.errors import SDKError
    root = Path(prefix).resolve(strict=True)
    qtpaths = root / QT_QTPATHS
    # A host prefix without Qt serves every other cross recipe. A Qt module
    # refuses the empty EMBERBSD_QT_HOST_PATH in qt6-qtbase/host-tools.mk.
    if not os.path.lexists(qtpaths):
        return ()
    if not qtpaths.is_file() or not os.access(qtpaths, os.X_OK):
        raise SDKError('The host prefix has an unusable native Qt qtpaths: ' + str(qtpaths))
    values = []
    for role, (variable, query) in QT_QUERIES.items():
        result = subprocess.run([str(qtpaths), '--query', query], capture_output=True, text=True,
                                env={'PATH': search_path, 'LC_ALL': 'C'})
        value = result.stdout.strip()
        if result.returncode != 0 or not os.path.isabs(value) or not Path(value).is_dir() \
                or not Path(value).resolve().is_relative_to(root):
            raise SDKError('qtpaths ' + query + ' does not name a directory in the host prefix')
        values.append((role, variable, value))
    return tuple(values)


# Cross lang/mlir runs these generators from the native mlir package. A host
# prefix without mlir maps nothing; lang/mlir refuses the empty variable.
MLIR_HOST_TOOLS = ('mlir-tblgen', 'mlir-pdll', 'mlir-src-sharder',
                   'mlir-linalg-ods-yaml-gen', 'mlir-irdl-to-cpp')


def mlir_host_tools(prefix):
    from emberbsd_sdk.errors import SDKError
    bindir = Path(prefix).resolve(strict=True) / 'bin'
    if not any(os.path.lexists(bindir / tool) for tool in MLIR_HOST_TOOLS):
        return ()
    for tool in MLIR_HOST_TOOLS:
        path = bindir / tool
        if not path.is_file() or not os.access(path, os.X_OK):
            raise SDKError('The host prefix has an incomplete native MLIR: ' + str(path))
    return (('mlir-tools-dir', 'EMBERBSD_MLIR_NATIVE_TOOLS', str(bindir)),)

# Cross Fortran packages run the native flang driver. Pin its real file: the
# driver searches the library directory beside that file, not beside the link.
def flang_host_tool(prefix):
    from emberbsd_sdk.errors import SDKError
    bindir = Path(prefix).resolve(strict=True) / 'bin'
    driver = bindir / 'flang'
    if not os.path.lexists(driver):
        return ()
    real = driver.resolve()
    if real.parent != bindir or not real.is_file() or not os.access(real, os.X_OK):
        raise SDKError('The host prefix has an invalid native flang: ' + str(driver))
    return (('flang', 'EMBERBSD_FLANG', str(real)),)

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


def render(toolset, qt=(), fetch_mode='fetch'):
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
    selected = [(role, variable, shlex.join((*toolset.command(role), '-p')) if role == 'gmkdir' else
                 shlex.join(toolset.command(role)) if role == 'as' else toolset.tool(role))
                for role, variable in ROLE_VARIABLES.items()]
    selected += [(role, variable, toolset.tool(role))
                 for role, variable in OPTIONAL_ROLES.items() if role in toolset.tools]
    if 'flex' in toolset.tools:
        selected.append(('lex', 'TOOLS_PLATFORM.lex', toolset.tool('flex')))
    selected += [(role + '-dir', variable, os.path.dirname(toolset.tool(role)))
                 for role, variable in ROLE_DIRECTORIES.items()]
    selected += list(qt)
    selected += [('sh-tool', 'TOOLS_PLATFORM.sh', toolset.tool('sh')),
                 ('awk-tool', 'TOOLS_PLATFORM.awk', toolset.tool('nawk')),
                 ('ar-tool', 'TOOLS_PLATFORM.ar', toolset.tool('ar')),
                 ('ranlib-tool', 'TOOLS_PLATFORM.ranlib', toolset.tool('ranlib')),
                 ('nm-tool', 'TOOLS_PLATFORM.nm', toolset.tool('nm')),
                 ('strip-tool', 'TOOLS_PLATFORM.strip', toolset.tool('strip'))]
    for role, variable, value in selected:
        value = literal(value)
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
    # Empty platform mappings make pkgsrc resolve these build tools through
    # the native package dependency rather than /usr/bin when absent.
    for role, variable in OPTIONAL_ROLES.items():
        if variable.startswith('TOOLS_PLATFORM.') and role not in toolset.tools:
            lines += [variable + '?=', '.if !empty(' + variable + ')',
                      '.error ' + variable + ' was not selected from the host prefix', '.endif']
    if 'flex' not in toolset.tools:
        lines += ['TOOLS_PLATFORM.lex?=', '.if !empty(TOOLS_PLATFORM.lex)',
                  '.error TOOLS_PLATFORM.lex was not selected from the host prefix', '.endif']
    # pkgsrc probes system directories for rpcgen independently of
    # TOOLS_PLATFORM. Refuse execution until the native package is installed.
    if 'rpcgen' not in toolset.tools:
        lines += ['TOOLS_PATH.rpcgen?= ${TOOLS_DIR}/bin/false',
                  '.if "${TOOLS_PATH.rpcgen}" != "${TOOLS_DIR}/bin/false"',
                  '.error TOOLS_PATH.rpcgen was not selected from the host prefix', '.endif']
    # The explicit manual mode supports only already available sources.
    if fetch_mode == 'fetch':
        value = literal(toolset.tool('fetch'))
        if "'" in value:
            from emberbsd_sdk.errors import SDKError
            raise SDKError('The native make mapping does not support quotes in tool paths')
        lines += ['_EMBER_SDK_FETCH:= ' + value,
                  '.if "${_EMBER_SDK_FETCH}" != "' + value + '"',
                  '.error _EMBER_SDK_FETCH differs from the selected Ports tool', '.endif',
                  'TOOLS_PLATFORM.fetch?= ${_EMBER_SDK_FETCH}',
                  '.if "${TOOLS_PLATFORM.fetch}" != "' + value + '"',
                  '.error TOOLS_PLATFORM.fetch differs from the selected Ports tool', '.endif']
    elif fetch_mode != 'manual':
        from emberbsd_sdk.errors import SDKError
        raise SDKError('Unsupported native fetch mode')
    lines += ['FETCH_USING?= ' + fetch_mode,
              '.if "${FETCH_USING}" != "' + fetch_mode + '"',
              '.error FETCH_USING differs from the selected fetch mode', '.endif']
    # Native platform probes can run before the child's MAKECONF include.
    lines += ['.export EMBERBSD_NATIVE_AWK']
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
    optional = tuple(role for role in OPTIONAL_ROLES
                     if any(os.path.lexists(Path(arguments.host_prefix) / directory / role)
                            for directory in ('bin', 'gnu/bin')))
    toolset = load_host_prefix(arguments.host_prefix,
                              required_roles=tuple(ROLE_VARIABLES) + tuple(ROLE_DIRECTORIES) + optional +
                              (('fetch',) if arguments.fetch_mode == 'fetch' else ()),
                              compiler_family=arguments.compiler_family)
    if Path(sys.executable).resolve(strict=True) != Path(toolset.tool('python')).resolve(strict=True):
        raise SDKError('The adapter interpreter differs from the selected Ports Python')
    return toolset


def write(toolset, destination, qt=(), fetch_mode='fetch'):
    from emberbsd_sdk import paths
    from emberbsd_sdk.errors import SDKError
    if not Path(destination).is_absolute():
        raise SDKError('Use an absolute native include destination')
    output = Path(paths.canonical_new(destination))
    data = render(toolset, qt, fetch_mode)
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
    parser.add_argument('--fetch-mode', choices=('fetch', 'manual'), default='fetch')
    parser.add_argument('--output')
    parser.add_argument('--makeconf')
    args = parser.parse_args(arguments)
    if args.operation == 'write':
        if not args.output or args.makeconf:
            parser.error('write requires only --output')
    elif not args.makeconf or args.output:
        parser.error('verify requires only --makeconf')
    toolset = selection(args)
    qt = qt_host_paths(args.host_prefix, toolset.path) + mlir_host_tools(args.host_prefix) + \
        flang_host_tool(args.host_prefix)
    if args.operation == 'write':
        print(json.dumps(write(toolset, args.output, qt, args.fetch_mode)))
        return
    from emberbsd_sdk import paths
    from emberbsd_sdk.errors import SDKError
    if not Path(args.makeconf).is_absolute():
        raise SDKError('Use an absolute native include path')
    path = Path(paths.canonical_existing(args.makeconf))
    paths.regular_file(str(path))
    data = path.read_bytes()
    if data != render(toolset, qt, args.fetch_mode):
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
