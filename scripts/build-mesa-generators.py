#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Replace the shell/Ruby orchestrator.
"""Build native Mesa shader generators with the shared Python and pkgsrc tools."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source

DEPENDENCIES = (
    'meson>=1.12.1', 'ninja-build>=1.13.2', 'cmake>=4.4.4', 'pkgconf>=0',
    'py315-mako>=1.4.3', 'py315-packaging>=26.3', 'py315-yaml>=6.0.3nb1',
    'py315-lxml>=6.1.3', 'py315-rnc2rng>=2.7.0',
    'py315-rply>=0.7.8', 'py315-appdirs>=1.4.4',
    'llvm>=23.1.4<23.1.5', 'clang>=23.1.4<23.1.5',
    'spirv-headers>=1.4.363.0', 'spirv-tools>=2026.4',
    'spirv-llvm-translator>=23.1.2<23.2',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive_pin(table, name):
    matches = []
    for line in table.read_text().splitlines():
        row = line.split('\t')
        if row[0] == name:
            matches.append(row[1:3])
        elif len(row) > 1 and row[1] == name:
            matches.append(row[2:4])
    require(len(matches) == 1 and len(matches[0]) == 2, 'Missing or duplicate archive pin: ' + name)
    digest, url = matches[0]
    require(re.fullmatch(r'[0-9a-f]{64}', digest) and url.startswith('https://'), 'Invalid archive pin: ' + name)
    return digest, url


HOST_ROLES = ('cc', 'cxx', 'cpp', 'ar', 'ranlib', 'nm', 'strip',
              'sh', 'python', 'cmake', 'meson', 'ninja', 'pkg-config',
              'pkg_info', 'llvm-config', 'flex', 'bison', 'bsdtar', 'patch',
              'curl', 'otool', 'spirv-val')


MODULE_QUERY = '''import importlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]).resolve()
names=['mesonbuild','mako','packaging','yaml','lxml.etree','rnc2rng','rply','appdirs']
modules={name:importlib.import_module(name) for name in names}
assert sys.version_info[:2] == (3,15)
assert all(pathlib.Path(module.__file__).resolve().is_relative_to(root) for module in modules.values())
assert modules['yaml'].__with_libyaml__
print(json.dumps({name:str(pathlib.Path(module.__file__).resolve()) for name,module in modules.items()}))
'''


def native_environment(native, sdk_root, temporary):
    from emberbsd_sdk.process import sanitized_environment
    environment = sanitized_environment()
    # A target SDK or an ambient toolchain must not affect the native build.
    for key in ('CC', 'CXX', 'CPP', 'AS', 'LD', 'AR', 'RANLIB', 'NM', 'STRIP',
                'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'CPATH',
                'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH', 'SDKROOT',
                'PKG_CONFIG_PATH', 'PKG_CONFIG_LIBDIR', 'PKG_CONFIG_SYSROOT_DIR',
                'CMAKE_PREFIX_PATH', 'CMAKE_TOOLCHAIN_FILE', 'CMAKE_GENERATOR',
                'DYLD_LIBRARY_PATH', 'DYLD_FALLBACK_LIBRARY_PATH',
                'GCC_EXEC_PREFIX', 'COMPILER_PATH', 'PYTHONPATH', 'PYTHONHOME'):
        environment.pop(key, None)
    for variable, role in (('CC', 'cc'), ('CXX', 'cxx'), ('CPP', 'cpp'),
                           ('AR', 'ar'), ('RANLIB', 'ranlib'), ('NM', 'nm'),
                           ('STRIP', 'strip'), ('SHELL', 'sh'), ('CMAKE', 'cmake'),
                           ('PKG_CONFIG', 'pkg-config'), ('LLVM_CONFIG', 'llvm-config')):
        environment[variable] = native.tool(role)
    host = Path(native.bundle_root)
    environment.update(PATH=native.path, HOST_PYTHON=native.tool('python'),
                       EMBERBSD_SDK_SOURCE=sdk_root, PYTHONDONTWRITEBYTECODE='1',
                       PYTHONNOUSERSITE='1', TMPDIR=str(temporary), TMP=str(temporary),
                       TEMP=str(temporary), CMAKE_PREFIX_PATH=str(host),
                       PKG_CONFIG_LIBDIR=os.pathsep.join(str(host / directory)
                           for directory in ('lib/pkgconfig', 'share/pkgconfig')))
    return environment


def native_file(native):
    # Meson accepts single-quoted Python-style strings and arrays.
    def value(words):
        return '[' + ', '.join(repr(str(word)) for word in words) + ']'
    names = {'c': 'cc', 'cpp': 'cxx', 'ar': 'ar', 'strip': 'strip',
             'pkg-config': 'pkg-config', 'llvm-config': 'llvm-config',
             'cmake': 'cmake', 'ninja': 'ninja', 'flex': 'flex', 'bison': 'bison',
             'python': 'python', 'python3': 'python', 'python3.15': 'python'}
    rows = ['[binaries]'] + [name + ' = ' + value(native.command(role))
                            for name, role in names.items()]
    host = Path(native.bundle_root)
    compile_flags = ['-I' + str(host / 'include')]
    link_flags = ['-L' + str(host / 'lib'), '-Wl,-rpath,' + str(host / 'lib'),
                  '-Wl,-rpath,' + str(host / 'gcc16/lib')]
    rows += ['', '[built-in options]', 'c_args = ' + value(compile_flags),
             'cpp_args = ' + value(compile_flags), 'c_link_args = ' + value(link_flags),
             'cpp_link_args = ' + value(link_flags)]
    return '\n'.join(rows) + '\n'


def mesa_commands(native, source, work, jobs, rtti):
    require(rtti in ('YES', 'NO'), 'Unexpected llvm-config --has-rtti result')
    destination = work / 'mesa'
    meson = native.command('python') + ('-B', '-E', '-s', native.tool('meson'))
    configure = [*meson, 'setup', str(destination), str(source),
        '--native-file', str(work / 'native.ini'), '--prefix', str(work / 'prefix'),
        '--wrap-mode=nodownload', '--buildtype=debugoptimized', '-Db_ndebug=false',
        '-Dcpp_rtti=' + ('true' if rtti == 'YES' else 'false'),
        '-Dauto_features=disabled', '-Dplatforms=[]', '-Dgallium-drivers=[]',
        '-Dvulkan-drivers=[]', '-Dglx=disabled', '-Degl=disabled', '-Dgbm=disabled',
        '-Dopengl=false', '-Dgles1=disabled', '-Dgles2=disabled',
        '-Dtools=imagination', '-Dmesa-clc=enabled', '-Dinstall-mesa-clc=true',
        '-Dprecomp-compiler=enabled', '-Dinstall-precomp-compiler=true',
        '-Dllvm=enabled', '-Dshared-llvm=enabled', '-Ddraw-use-llvm=false',
        '-Damd-use-llvm=false', '-Dspirv-tools=enabled', '-Dbuild-tests=true']
    return [('configure-mesa', configure),
            ('build-mesa', [native.tool('ninja'), '-C', str(destination), '-j', str(jobs)]),
            ('test-mesa', [*meson, 'test', '-C', str(destination), '--no-rebuild',
                           '--print-errorlogs', '--num-processes', str(jobs)]),
            ('install-mesa', [*meson, 'install', '-C', str(destination), '--no-rebuild'])]


def check_compilers(native, build):
    metadata = json.loads((build / 'meson-info/intro-compilers.json').read_text())
    for language, role in (('c', 'cc'), ('cpp', 'cxx')):
        compiler = metadata['host'][language]
        require(compiler['id'] == 'gcc' and compiler['exelist'] == list(native.command(role)),
                'Meson selected a different native compiler: ' + language)
        require(compiler['version'].split('.')[0] == '16', 'Meson did not select GCC16')


def build(arguments, sdk_root):
    from emberbsd_sdk.errors import ProcessOwnershipError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json
    from emberbsd_sdk.paths import canonical_new, entry, real_directory, reject_overlap
    from emberbsd_sdk.process import ContextLocks, run_logged
    from emberbsd_sdk.native_toolset import load_host_prefix
    from emberbsd_sdk.stream import capture_streamed

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('intel', 'powervr', 'all'), default='powervr')
    parser.add_argument('--host-prefix', required=True)
    parser.add_argument('--pkgdb', required=True, help='Package database used by the native prefix')
    parser.add_argument('--lock-directory', required=True, help='Shared SDK producer lock namespace')
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('work')
    parser.add_argument('distdir')
    args = parser.parse_args(arguments)
    require(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'The native generators require macOS ARM64')
    require(1 <= args.jobs <= 256, 'Use a positive job count no greater than 256')
    for value in (args.host_prefix, args.pkgdb, args.lock_directory, args.work, args.distdir):
        require(re.fullmatch(r'/[A-Za-z0-9_./-]+', value), 'Use absolute paths without shell metacharacters')
    host = Path(args.host_prefix).resolve(strict=True)
    distdir = Path(args.distdir).resolve(strict=True)
    pkgdb = Path(args.pkgdb).resolve(strict=True)
    lock_directory = Path(args.lock_directory).resolve(strict=True)
    real_directory(str(pkgdb))
    real_directory(str(lock_directory))
    real_directory(str(host))
    real_directory(str(distdir))
    reject_overlap(str(host), str(distdir))
    work = Path(canonical_new(args.work))
    real_directory(str(work.parent))
    require(entry(str(work)) is None, 'NEW_WORK must not exist; preserve earlier work')
    for value in (host, pkgdb, distdir, PORTS):
        reject_overlap(str(work), str(value))
    # Match the package writer's namespace and retain read leases through sealing.
    with ContextLocks([str(host), str(pkgdb)], str(lock_directory), shared=True):
        native = load_host_prefix(host, required_roles=HOST_ROLES)
        python = Path(native.tool('python'))
        require(python.resolve(strict=True) == Path(sys.executable).resolve(strict=True),
                'Run this command with Python 3.15 from the selected host prefix')
        tools = native.tools
        graphics = PORTS / 'profiles/common-graphics'
        helpers = PORTS / 'probes/a733-accelerators/host-tools'
        objc_patch = PORTS / 'pkgsrc/graphics/MesaLib/patches/patch-meson.build-host-objc'
        scripts = [Path(__file__).resolve(), graphics / 'cross/seal-mesa-generators.py',
                   helpers / 'mesa-26.2.4-pco-bvnc.patch', objc_patch,
                   PORTS / 'pkgsrc/graphics/MesaLib/patches/patch-src_imagination_common_pvr__iface.h',
                   graphics / 'sources.tsv']
        scripts.append(Path(sdk_source.__file__).resolve())
        scripts.extend(sorted((Path(sdk_root) / 'src/emberbsd_sdk').rglob('*.py')))
        source_hashes = {str(path): sha256_file(str(path)) for path in scripts}
        with ContextLocks([str(work)], str(work.parent)):
            require(entry(str(work)) is None, 'NEW_WORK appeared before creation')
            work.mkdir()
            (work / 'tmp').mkdir()
            (work / 'logs').mkdir()
            environment = native_environment(native, sdk_root, work / 'tmp')

            def query(argv):
                result = capture_streamed(list(map(str, argv)), env=environment, timeout=120,
                                          stdout_limit=16 * 1024 * 1024, stderr_limit=1024 * 1024)
                require(not result.stderr_truncated, 'Native preflight stderr exceeds its limit')
                return result.value.decode('utf-8').strip()

            def run(argv, name, cwd=None):
                try:
                    run_logged(list(map(str, argv)), str(work / 'logs' / (name + '.log')), cwd=cwd, env=environment)
                except ProcessOwnershipError as error:
                    write_json(str(work / sdk_source.PRODUCER_QUARANTINE), dict(error=str(error), step=name))
                    raise

            providers = {pattern: query([tools['pkg_info'], '-K', str(pkgdb), '-e', pattern]) for pattern in DEPENDENCIES}
            require(all(providers.values()), 'Missing native package dependency')
            modules = json.loads(query([python, '-B', '-E', '-s', '-c', MODULE_QUERY, str(host)]))
            provider_paths = {str(path): str(path.resolve(strict=True)) for path in [python, *map(Path, tools.values()), *map(Path, modules.values())]}
            write_json(str(work / 'inputs.json'), dict(source=source_hashes, providers=providers, modules=modules,
                       provider_paths=provider_paths, native_tools=native.as_dict(),
                       python=str(python.resolve(strict=True)), jobs=args.jobs, profile=args.profile,
                       native_compiler='Ports host GCC16; no target objects'))

            def fetch(name, table):
                digest, url = archive_pin(table, name)
                destination = distdir / name
                with ContextLocks([str(destination)], str(work)):
                    if not os.path.lexists(destination):
                        fd, temporary = tempfile.mkstemp(prefix='.' + name + '.part-', dir=distdir)
                        os.close(fd)
                        print('Retained download on failure: ' + temporary, file=sys.stderr, flush=True)
                        run([tools['curl'], '-fL', '--proto', '=https', '--proto-redir', '=https', '-o', temporary, url], 'fetch-' + name)
                        require(sha256_file(temporary) == digest, 'Wrong downloaded archive SHA256: ' + name)
                        os.chmod(temporary, 0o644)
                        os.link(temporary, destination)
                        os.unlink(temporary)
                    require(destination.is_file() and sha256_file(str(destination.resolve(strict=True))) == digest, 'Wrong archive SHA256: ' + name)
                return destination.resolve(strict=True)

            mesa_archive = fetch('mesa-26.2.5.tar.xz', graphics / 'sources.tsv')
            require(query([tools['llvm-config'], '--version']) == '23.1.4',
                    'Native LLVM must match the shared Mesa dependency')
            llvm_prefix = Path(query([tools['llvm-config'], '--prefix'])).resolve(strict=True)
            require(llvm_prefix == host, 'llvm-config selects a different prefix')
            rtti = query([tools['llvm-config'], '--has-rtti'])
            extract = work / 'mesa-extract'
            extract.mkdir()
            run([tools['bsdtar'], '-xJf', mesa_archive, '-C', extract], 'mesa-extract')
            source = extract / 'mesa-26.2.5'
            run([tools['patch'], '--posix', '-f', '-N', '-F', '0', '-p1', '-d', source, '-i', helpers / 'mesa-26.2.4-pco-bvnc.patch'], 'mesa-bvnc-patch')
            run([tools['patch'], '--posix', '-f', '-N', '-F', '0', '-p0',
                 '-d', source, '-i', objc_patch], 'mesa-host-objc-patch')
            source.rename(work / 'mesa-source')
            extract.rmdir()
            native_work = work / 'native'
            native_work.mkdir()
            (native_work / 'native.ini').write_text(native_file(native))
            for name, command in mesa_commands(native, work / 'mesa-source', native_work, args.jobs, rtti):
                run(command, name)
                if name == 'configure-mesa':
                    check_compilers(native, native_work / 'mesa')
            sealer = load(graphics / 'cross/seal-mesa-generators.py', 'mesa_native_sealer')
            sealer.seal(['--profile', args.profile, '--host-prefix', str(host), '--pkgdb', str(pkgdb),
                         '--lock-directory', str(lock_directory), str(mesa_archive), str(work / 'mesa-source'),
                         str(work / 'native/mesa'), tools['spirv-val'], str(work / 'sealed')])
            require(source_hashes == {path: sha256_file(path) for path in source_hashes}, 'Builder source changed during the native build')
            require(provider_paths == {path: str(Path(path).resolve(strict=True)) for path in provider_paths}, 'Selected native tool or module path changed')
            require(providers == {pattern: query([tools['pkg_info'], '-K', str(pkgdb), '-e', pattern]) for pattern in DEPENDENCIES},
                    'Native package providers changed during the build')
            write_json(str(work / 'outputs.json'), dict(sealed=str(work / 'sealed'),
                       manifest_sha256=sha256_file(str(work / 'sealed/installed.sha256'))))
    print('Set EMBERBSD_MESA_GENERATORS=' + str(work / 'sealed') + ' in the cross MAKECONF.')


if __name__ == '__main__':
    sdk_source.install_signal_handlers()
    try:
        require(sys.version_info[:2] == (3, 15), 'Host Python 3.15 is required')
        sdk_root, arguments = sdk_source.load_sdk()
        build(arguments, sdk_root)
    except Exception as error:
        sdk_source.exit_error(error)
