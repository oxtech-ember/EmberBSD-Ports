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


def khronos_pins(helpers):
    result = dict(load(helpers / 'build-deps.py', 'mesa_native_dependency_policy').SOURCE_PINS)
    require(set(result) == {'SPIRV-Headers', 'SPIRV-LLVM-Translator'}, 'Unsupported Khronos dependency source set')
    result['SPIRV-Tools'] = load(helpers / 'apply-spirv-tools-patches.py', 'mesa_spirv_source_policy').PIN
    require(all(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{40}', value) for value in result.values()), 'Invalid Khronos source pin')
    return result


def build(arguments, sdk_root):
    from emberbsd_sdk.errors import ProcessOwnershipError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json
    from emberbsd_sdk.paths import canonical_new, entry, real_directory, reject_overlap
    from emberbsd_sdk.process import ContextLocks, run_logged, sanitized_environment
    from emberbsd_sdk.stream import capture_streamed

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('intel', 'powervr', 'all'), default='powervr')
    parser.add_argument('--host-prefix', required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('work')
    parser.add_argument('distdir')
    args = parser.parse_args(arguments)
    require(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'The native generators require macOS ARM64')
    require(1 <= args.jobs <= 256, 'Use a positive job count no greater than 256')
    for value in (args.host_prefix, args.work, args.distdir):
        require(re.fullmatch(r'/[A-Za-z0-9_./-]+', value), 'Use absolute paths without shell metacharacters')
    host = Path(args.host_prefix).resolve(strict=True)
    distdir = Path(args.distdir).resolve(strict=True)
    real_directory(str(host))
    real_directory(str(distdir))
    reject_overlap(str(host), str(distdir))
    work = Path(canonical_new(args.work))
    real_directory(str(work.parent))
    require(entry(str(work)) is None, 'NEW_WORK must not exist; preserve earlier work')
    for value in (host, distdir, PORTS):
        reject_overlap(str(work), str(value))
    python = host / 'bin/python3.15'
    require(python.resolve(strict=True) == Path(sys.executable).resolve(strict=True),
            'Run this command with the selected HOST_PREFIX/bin/python3.15')
    tools = {name: host / 'bin' / name for name in ('cmake', 'ninja', 'pkg-config')}
    tools['pkg_info'] = host / 'sbin/pkg_info'
    require(all(os.access(path, os.X_OK) for path in tools.values()), 'Missing native pkgsrc tool')
    cross = PORTS / 'profiles/common-build-tools/cross'
    graphics = PORTS / 'profiles/common-graphics'
    helpers = PORTS / 'probes/a733-accelerators/host-tools'
    scripts = [Path(__file__).resolve(), cross / 'prepare-llvm-macos.py', cross / 'llvm_host.py',
               graphics / 'cross/seal-mesa-generators.py', helpers / 'build-deps.py', helpers / 'configure-host.sh',
               helpers / 'prepare-llvm-include-overlay.py', helpers / 'llvm-include-wrapper.sh',
               helpers / 'apply-spirv-tools-patches.py', helpers / 'check-spirv-link-order.py',
               helpers / 'spirv-tools-2026.4-function-order.patch', helpers / 'mesa-26.2.4-pco-bvnc.patch',
               PORTS / 'pkgsrc/graphics/MesaLib/patches/patch-src_imagination_common_pvr__iface.h',
               graphics / 'sources.tsv', PORTS / 'profiles/common-build-tools/sources.tsv']
    scripts.append(Path(sdk_source.__file__).resolve())
    scripts.extend(sorted((Path(sdk_root) / 'src/emberbsd_sdk').rglob('*.py')))
    source_hashes = {str(path): sha256_file(str(path)) for path in scripts}
    with ContextLocks([str(work)], str(work.parent)):
        require(entry(str(work)) is None, 'NEW_WORK appeared before admission')
        work.mkdir()
        (work / 'tmp').mkdir()
        (work / 'logs').mkdir()
        environment = sanitized_environment()
        environment.update(HOST_PYTHON=str(python), EMBERBSD_SDK_SOURCE=sdk_root,
                           CMAKE=str(tools['cmake']), JOBS=str(args.jobs), PYTHONDONTWRITEBYTECODE='1',
                           TMPDIR=str(work / 'tmp'), TMP=str(work / 'tmp'), TEMP=str(work / 'tmp'),
                           PATH=f'{host}/bin:/usr/bin:/bin:/usr/sbin:/sbin')

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

        providers = {pattern: query([tools['pkg_info'], '-e', pattern]) for pattern in DEPENDENCIES}
        require(all(providers.values()), 'Missing native package dependency')
        module_query = '''import importlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]).resolve()
names=['mesonbuild','mako','packaging','yaml','lxml.etree','rnc2rng','rply','appdirs']
modules={name:importlib.import_module(name) for name in names}
assert sys.version_info[:2] == (3,15)
assert all(pathlib.Path(module.__file__).resolve().is_relative_to(root) for module in modules.values())
assert modules['yaml'].__with_libyaml__
print(json.dumps({name:str(pathlib.Path(module.__file__).resolve()) for name,module in modules.items()}))
'''
        modules = json.loads(query([python, '-B', '-E', '-c', module_query, str(host)]))
        provider_paths = {str(path): str(path.resolve(strict=True)) for path in [python, *tools.values(), *map(Path, modules.values())]}
        provider_hashes = {path: sha256_file(path) for path in provider_paths.values()}
        write_json(str(work / 'inputs.json'), dict(source=source_hashes, providers=providers, modules=modules,
                   provider_paths=provider_paths, provider_sha256=provider_hashes,
                   python=str(python.resolve(strict=True)), jobs=args.jobs, profile=args.profile,
                   native_compiler='Pinned upstream macOS LLVM/Clang SDK; no target objects'))

        def fetch(name, table):
            digest, url = archive_pin(table, name)
            destination = distdir / name
            with ContextLocks([str(destination)], str(work)):
                if not os.path.lexists(destination):
                    fd, temporary = tempfile.mkstemp(prefix='.' + name + '.part-', dir=distdir)
                    os.close(fd)
                    print('Retained download on failure: ' + temporary, file=sys.stderr, flush=True)
                    run(['curl', '-fL', '--proto', '=https', '--proto-redir', '=https', '-o', temporary, url], 'fetch-' + name)
                    require(sha256_file(temporary) == digest, 'Wrong downloaded archive SHA256: ' + name)
                    os.chmod(temporary, 0o644)
                    os.link(temporary, destination)
                    os.unlink(temporary)
                require(destination.is_file() and sha256_file(str(destination.resolve(strict=True))) == digest, 'Wrong archive SHA256: ' + name)
            return destination.resolve(strict=True)

        mesa_archive = fetch('mesa-26.2.5.tar.xz', graphics / 'sources.tsv')
        llvm_archive = fetch('LLVM-23.1.4-macOS-ARM64.tar.xz', PORTS / 'profiles/common-build-tools/sources.tsv')
        # Import this producer into the current controller. Do not nest an owned
        # controller around its owned version/dependency commands.
        sys.path.insert(0, str(cross))
        prepare = load(cross / 'prepare-llvm-macos.py', 'mesa_native_llvm')
        previous_environment = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update(environment)
            prepare.prepare([str(llvm_archive), str(work / 'llvm-sdk')])
        finally:
            os.environ.clear()
            os.environ.update(previous_environment)
        sdk = work / 'llvm-sdk/LLVM-23.1.4-macOS-ARM64'
        for name, revision in khronos_pins(helpers).items():
            source = work / 'deps/src' / name
            source.mkdir(parents=True)
            run(['git', '-C', source, 'init', '-q'], 'init-' + name)
            run(['git', '-C', source, 'remote', 'add', 'origin', 'https://github.com/KhronosGroup/' + name + '.git'], 'remote-' + name)
            run(['git', '-C', source, 'fetch', '--depth', '1', 'origin', revision], 'fetch-' + name)
            run(['git', '-C', source, 'checkout', '--detach', revision], 'checkout-' + name)
        dependencies = load(helpers / 'build-deps.py', 'mesa_native_dependencies')
        previous_environment = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update(environment)
            dependencies.build([str(work / 'deps'), str(sdk), str(host)])
        finally:
            os.environ.clear()
            os.environ.update(previous_environment)
        extract = work / 'mesa-extract'
        extract.mkdir()
        run(['tar', '-xJf', mesa_archive, '-C', extract], 'mesa-extract')
        source = extract / 'mesa-26.2.5'
        run(['patch', '--no-backup-if-mismatch', '-f', '-N', '-F', '0', '-p1', '-d', source, '-i', helpers / 'mesa-26.2.4-pco-bvnc.patch'], 'mesa-bvnc-patch')
        source.rename(work / 'mesa-source')
        extract.rmdir()
        run(['sh', helpers / 'configure-host.sh', work / 'native', work / 'mesa-source', sdk, host, work / 'deps/prefix'], 'build-mesa')
        sealer = load(graphics / 'cross/seal-mesa-generators.py', 'mesa_native_sealer')
        sealer.seal(['--profile', args.profile, str(mesa_archive), str(work / 'mesa-source'),
                     str(work / 'native/mesa'), str(work / 'deps/prefix/bin/spirv-val'), str(work / 'sealed')])
        require(source_hashes == {path: sha256_file(path) for path in source_hashes}, 'Builder source changed during the native build')
        require(provider_paths == {path: str(Path(path).resolve(strict=True)) for path in provider_paths}, 'Selected native tool or module path changed')
        require(provider_hashes == {path: sha256_file(path) for path in provider_hashes}, 'Selected native provider changed during the build')
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
