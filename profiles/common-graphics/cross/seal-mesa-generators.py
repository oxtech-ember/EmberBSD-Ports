#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Port of the native Ruby sealer.
"""Seal real native Mesa generators and their upstream interface inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import struct
import sys

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source

MESA_SHA256 = '794b3d1729075dae7ebd47c7283b7ca0cdb5dec668f7f11cc0a5d82f6138a0a5'


def sha(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def profiles_for(profile):
    require(profile in ('intel', 'powervr', 'all'), 'Use profile intel, powervr or all')
    return ['intel', 'powervr'] if profile == 'all' else [profile]


def input_records(inputs):
    directories = sorted({str(path) for path in inputs if path.is_dir()})
    files = [path for path in inputs if not path.is_dir()]
    for directory in directories:
        manifest = Path(directory) / '.emberbsd-include-overlay.tsv'
        if manifest.is_file():
            files.append(manifest)
    return {str(path): sha(path) for path in files}, directories


def shader_dependencies(path, build, virtual_headers):
    text = path.read_text().replace('\\\n', ' ')
    require(':' in text, 'Malformed common shader depfile')
    result = set()
    for name in shlex.split(text.split(':', 1)[1]):
        candidate = os.path.abspath(build / name)
        result.add(virtual_headers[candidate] if candidate in virtual_headers
                   else str(Path(candidate).resolve(strict=True)))
    require(result, 'Empty common shader dependency set')
    return sorted(result)


def select_host(prefix):
    from emberbsd_sdk.native_toolset import load_host_prefix
    return load_host_prefix(prefix, required_roles=('bsdtar', 'patch', 'otool', 'spirv-val'))


def sealing_environment(native, temporary, overrides):
    from emberbsd_sdk.process import sanitized_environment
    env = sanitized_environment()
    env.update(TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary))
    env.update(overrides)
    env['PATH'] = native.path
    return env


def patch_command(native, directory, patch, strip):
    return [native.tool('patch'), '--posix', '-f', '-N', '-F0', '-p' + str(strip),
            '-d', directory, '-i', patch]


def system_library(path):
    return path.is_absolute() and os.path.normpath(path) == str(path) and any(
        str(path).startswith(root) for root in ('/usr/lib/', '/System/Library/'))


def dependency_metadata(listing, commands):
    """Read selected otool's text interface. Do not parse Mach-O bytes here."""
    load_commands = {'LC_LOAD_DYLIB', 'LC_LOAD_WEAK_DYLIB', 'LC_REEXPORT_DYLIB',
                     'LC_LOAD_UPWARD_DYLIB', 'LC_LAZY_LOAD_DYLIB'}
    loads, rpaths, identity = [], [], None
    blocks = re.split(r'^Load command [0-9]+\s*$', commands, flags=re.M)
    require(len(blocks) > 1, 'Missing otool load commands')
    for block in blocks[1:]:
        kind = re.search(r'^\s*cmd (\S+)\s*$', block, re.M)
        require(kind is not None, 'Missing otool load-command name')
        kind = kind[1]
        require(kind.startswith('LC_') and (not kind.startswith('LC_LOAD_') or
                kind in load_commands | {'LC_LOAD_DYLINKER'}), 'Unrecognized otool load command: ' + kind)
        require(kind not in ('LC_DYLD_ENVIRONMENT', 'LC_LAZY_DYLIB_INFO'),
                'Unsupported environment or indirect lazy dependency metadata: ' + kind)
        if kind in load_commands | {'LC_ID_DYLIB', 'LC_RPATH', 'LC_LOAD_DYLINKER'}:
            field = 'path' if kind == 'LC_RPATH' else 'name'
            names = re.findall(r'^\s*' + field + r' (.+) \(offset [0-9]+\)\s*$', block, re.M)
            require(len(names) == 1 and not any(ord(c) < 32 for c in names[0]),
                    'Malformed otool dependency path')
            name = names[0]
            if kind in load_commands:
                loads.append(name)
            elif kind == 'LC_RPATH':
                rpaths.append(name)
            elif kind == 'LC_LOAD_DYLINKER':
                require(system_library(Path(name)), 'Non-system native loader')
            else:
                require(identity is None, 'Duplicate dylib install name')
                identity = name
    listed = []
    for line in listing.splitlines()[1:]:
        match = re.fullmatch(r'\s+(.+) \(compatibility version [^,]+, current version [^)]+\)(?: \[[^]]+\])?\s*', line)
        require(match is not None, 'Malformed otool dependency listing')
        listed.append(match[1])
    require(sorted(listed) == sorted(loads + ([identity] if identity is not None else [])),
            'otool -L and load commands disagree')
    return dict(loads=loads, rpaths=rpaths)


def native_dependencies(executable, prefix, inspect):
    """Resolve actual runtime paths. OS ABI images terminate this policy graph."""
    executable, prefix = executable.resolve(strict=True), prefix.resolve(strict=True)

    def expand(name, owner):
        for token, base in (('@loader_path', owner.parent), ('@executable_path', executable.parent)):
            if name == token or name.startswith(token + '/'):
                return base / name[len(token):].lstrip('/')
        require(name.startswith('/'), 'Unsupported relative runtime path: ' + name)
        return Path(name)

    def member(candidate):
        if system_library(candidate):
            return None
        actual = candidate.resolve(strict=True)
        require(actual.is_relative_to(prefix) and actual != prefix,
                'Native shared dependency escapes host prefix: ' + str(candidate))
        require(actual.is_file(), 'Native shared dependency is not a file: ' + str(candidate))
        return actual

    pending, seen, images, inputs = [(executable, ())], set(), {}, {}
    while pending:
        owner, inherited = pending.pop()
        if owner not in images:
            require(len(images) < 1024, 'Native dependency graph exceeds its limit')
            images[owner] = inspect(owner)
            inputs[str(owner)] = images[owner]['sha256']
        image = images[owner]
        search = tuple(dict.fromkeys([str(expand(path, owner)) for path in image['rpaths']] + list(inherited)))
        state = (owner, search)
        if state in seen:
            continue
        require(len(seen) < 4096, 'Native dependency contexts exceed their limit')
        seen.add(state)
        for name in image['loads']:
            if name.startswith('@rpath/'):
                leaf = name[len('@rpath/'):]
                require(leaf and all(part not in ('', '.', '..') for part in leaf.split('/')),
                        'Invalid rpath dependency: ' + name)
                candidate = next((Path(root) / leaf for root in search
                                  if os.path.lexists(Path(root) / leaf)), None)
                require(candidate is not None, 'Unresolved native rpath dependency: ' + name)
            else:
                candidate = expand(name, owner)
            target = member(candidate)
            if target is not None:
                pending.append((target, search))
    return inputs


def seal(arguments):
    from emberbsd_sdk.paths import canonical_new, reject_overlap
    from emberbsd_sdk.process import ContextLocks

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('intel', 'powervr', 'all'), default='powervr')
    parser.add_argument('--host-prefix', required=True, type=Path)
    parser.add_argument('--pkgdb', required=True, type=Path)
    parser.add_argument('--lock-directory', required=True, type=Path)
    parser.add_argument('archive')
    parser.add_argument('source')
    parser.add_argument('build')
    parser.add_argument('validator')
    parser.add_argument('work')
    args = parser.parse_args(arguments)
    for name in ('host_prefix', 'pkgdb', 'lock_directory'):
        path = getattr(args, name)
        require(path.is_absolute(), '--' + name.replace('_', '-') + ' must be absolute')
        path = path.resolve(strict=True)
        require(path.is_dir(), 'Expected directory: ' + str(path))
        setattr(args, name, path)
    args.work = canonical_new(args.work)
    for protected in (args.host_prefix, args.pkgdb, args.source, args.build):
        reject_overlap(args.work, protected)
    with ContextLocks([str(args.host_prefix), str(args.pkgdb)], str(args.lock_directory), shared=True):
        seal_locked(args)


def seal_locked(args):
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
    from emberbsd_sdk.paths import regular_file, verify_stable
    from emberbsd_sdk.process import ContextLocks
    from emberbsd_sdk.stream import capture_streamed

    values = [getattr(args, name) for name in ('archive', 'source', 'build', 'validator', 'work')]
    require(all(re.fullmatch(r'/[A-Za-z0-9_./-]+', value) for value in values),
            'Use absolute paths without whitespace or shell metacharacters')
    archive, source, build, validator = [Path(value).resolve(strict=True) for value in values[:4]]
    work = Path(args.work)
    require(not os.path.lexists(work), 'NEW_WORK must not exist')
    require(platform.system() == 'Darwin' and platform.machine() == 'arm64',
            'This native generator recipe requires macOS ARM64')
    native = select_host(args.host_prefix)
    prefix = Path(native.bundle_root)
    require(validator == Path(native.tool('spirv-val')).resolve(strict=True),
            'Validator must be the selected host-prefix spirv-val')
    profiles = profiles_for(args.profile)
    require(sha(archive) == MESA_SHA256, 'Wrong Mesa source archive')
    require((source / 'VERSION').read_text().strip() == '26.2.5', 'Wrong Mesa source version')
    metadata = build / 'meson-info'
    info = json.loads((metadata / 'meson-info.json').read_text())
    require(Path(info['directories']['source']).resolve(strict=True) == source,
            'Native build uses another source tree')
    project = json.loads((metadata / 'intro-projectinfo.json').read_text())
    require(project['version'] == '26.2.5', 'Wrong Mesa build version')
    options = {row['name']: row['value'] for row in json.loads((metadata / 'intro-buildoptions.json').read_text())}
    require(options['b_ndebug'] == 'false', 'Native tools must retain assertions')
    require('23.1.4' in (build / 'build.ninja').read_text(), 'Native tools must use LLVM23')
    tools = {'mesa_clc': 'src/compiler/clc/mesa_clc', 'vtn_bindgen2': 'src/compiler/spirv/vtn_bindgen2'}
    if 'powervr' in profiles:
        tools['pco_clc'] = 'src/imagination/pco/uscgen/pco_clc'
    commands = []
    with ContextLocks([str(work)], str(work.parent)):
        work.mkdir()
        (work / 'tmp').mkdir()

        def run(argv, name, overrides=None):
            argv = list(map(str, argv))
            overrides = {} if overrides is None else overrides
            commands.append(dict(argv=argv, cwd=str(build), environment=overrides))
            env = sealing_environment(native, work / 'tmp', overrides)
            try:
                result = capture_streamed(argv, cwd=str(build), env=env, timeout=600,
                                          stdout_limit=16 * 1024 * 1024, stderr_limit=1024 * 1024)
                (work / (name + '.stdout')).write_bytes(result.value)
                (work / (name + '.stderr')).write_bytes(result.stderr)
                require(not result.stderr_truncated, 'Generator stderr exceeds the capture limit')
                return result.value.decode('utf-8')
            except CommandError as error:
                (work / (name + '.stdout')).write_bytes(error.stdout)
                (work / (name + '.stderr')).write_bytes(error.stderr)
                raise
            except ProcessOwnershipError as error:
                write_json(work / sdk_source.PRODUCER_QUARANTINE, dict(error=str(error), argv=argv))
                raise

        runtime_inputs = {}

        def check_runtime(binary, name):
            index = 0

            def inspect(path):
                nonlocal index
                index += 1
                before = regular_file(path)
                label = name + '-runtime-' + str(index)
                listing = run([native.tool('otool'), '-arch', 'arm64', '-L', path], label + '-libraries')
                commands = run([native.tool('otool'), '-arch', 'arm64', '-l', path], label + '-commands')
                result = dependency_metadata(listing, commands)
                result['sha256'] = sha(path)
                verify_stable(path, before)
                return result

            found = native_dependencies(binary, prefix, inspect)
            require(all(path not in runtime_inputs or runtime_inputs[path] == digest
                        for path, digest in found.items()), 'Native runtime changed during sealing')
            runtime_inputs.update(found)

        for name, path in tools.items():
            binary = build / path
            require(os.access(binary, os.X_OK), 'Missing real native tool: ' + str(binary))
            with binary.open('rb') as stream:
                require(stream.read(8) == struct.pack('<II', 0xfeedfacf, 0x0100000c), 'Expected native ARM64 Mach-O')
            check_runtime(binary, name)
        require(os.access(validator, os.X_OK), 'Missing SPIR-V validator')
        check_runtime(validator, 'validator')
        bvnc_patch = PORTS / 'probes/a733-accelerators/host-tools/mesa-26.2.4-pco-bvnc.patch'
        objc_patch = PORTS / 'pkgsrc/graphics/MesaLib/patches/patch-meson.build-host-objc'
        interface_patch = PORTS / 'pkgsrc/graphics/MesaLib/patches/patch-src_imagination_common_pvr__iface.h'
        inputs = [Path(__file__).resolve(), archive, validator, build / 'build.ninja',
                  build / 'compile_commands.json', bvnc_patch, objc_patch, interface_patch]
        targets = json.loads((metadata / 'intro-targets.json').read_text())
        for name, path in tools.items():
            selected = [row for row in targets if row['name'] == name and row['type'] == 'executable']
            require(len(selected) == 1 and selected[0]['filename'] == [str(build / path)], 'Missing real Meson target: ' + name)
            inputs.append(build / path)
            for group in selected[0]['target_sources']:
                inputs.extend(Path(p) for key in ('compiler', 'linker') for p in group.get(key, []))
                inputs.extend((build / arg).resolve(strict=True) for arg in group.get('parameters', []) if arg.endswith(('.a', '.tbd')))
        inputs.extend(metadata.glob('*.json'))
        input_hashes, directory_inputs = input_records(inputs)
        input_hashes.update(runtime_inputs)
        reference = work / 'reference'
        reference.mkdir()
        run([native.tool('bsdtar'), '-xf', archive, '--strip-components=1', '-C', reference], 'extract')
        pco = 'src/imagination/pco/uscgen/pco_clc.c'
        if sha(reference / pco) != sha(source / pco):
            run(patch_command(native, reference, bvnc_patch, 1), 'bvnc-patch')
        if sha(reference / 'meson.build') != sha(source / 'meson.build'):
            run(patch_command(native, reference, objc_patch, 0), 'host-objc-patch')
        source_hashes = {}
        for path in sorted(reference.rglob('*')):
            if path.is_file():
                relative = str(path.relative_to(reference))
                require((source / relative).is_file() and sha(path) == sha(source / relative),
                        'Native source differs from the pinned source: ' + relative)
                source_hashes[relative] = sha(path)
        (work / 'source.sha256').write_text(''.join(f'{digest}  {path}\n' for path, digest in source_hashes.items()))
        for name in ('bin', 'smoke', 'metadata'):
            (work / name).mkdir()
        for name, path in tools.items():
            shutil.copy2(build / path, work / 'bin' / name)
            check_runtime(work / 'bin' / name, name + '-copied')
        input_hashes.update(runtime_inputs)
        for name in ('meson-info.json', 'intro-projectinfo.json', 'intro-buildoptions.json', 'intro-targets.json', 'intro-dependencies.json'):
            shutil.copy2(metadata / name, work / 'metadata' / name)
        for name in ('build.ninja', 'compile_commands.json'):
            shutil.copy2(build / name, work / 'metadata' / name)
        run(patch_command(native, reference, interface_patch, 0), 'interface-patch')
        interfaces = ['src/compiler/nir/nir.h', 'src/compiler/nir/nir_serialize.c', 'src/compiler/nir/nir_intrinsics.py', 'src/compiler/spirv/spirv_to_nir.c']
        if 'powervr' in profiles:
            interfaces += ['src/imagination/' + p for p in ('common/pvr_iface.h', 'pco/pco.h', 'pco/pco_common.h.py', 'pco/usclib/common.cl', 'pco/usclib/sync.cl', 'pco/usclib/tex.cl')]
        if 'intel' in profiles:
            interfaces += ['src/intel/shaders/' + p for p in ('libintel_shaders.h', 'dgc.cl', 'dgc_debug.cl', 'generate.cl', 'generate_draws.cl', 'generate_draws_iris.cl', 'query_copy.cl', 'util.cl')]
        (work / 'interface.sha256').write_text(''.join(f'{sha(reference / path)}  {path}\n' for path in interfaces))
        lines = [line for line in (build / 'build.ninja').read_text().splitlines()
                 if line.startswith(' COMMAND = ') and 'mesa_clc -o src/imagination/pco/usclib/pco_usclib.spv ' in line]
        require(lines, 'Missing genuine upstream common-shader command')
        argv = shlex.split(lines[0].removeprefix(' COMMAND = ').strip())
        require((build / argv[0]).resolve(strict=True) == (build / tools['mesa_clc']).resolve(strict=True), 'Unexpected build compiler')
        require('--' in argv, 'Missing compiler delimiter')
        shader_inputs = [arg for arg in argv[1:argv.index('--')] if not arg.startswith('-')]
        require(sum(arg.endswith('.cl') for arg in shader_inputs) == 3, 'Unexpected shader source in native command')
        for name in ('common', 'sync', 'tex'):
            expected = source / ('src/imagination/pco/usclib/' + name + '.cl')
            require(any(Path(os.path.abspath(build / arg)) == expected for arg in shader_inputs), 'Incomplete common shader inputs')
        argv[0] = str(work / 'bin/mesa_clc')
        argv[argv.index('-o') + 1] = str(work / 'smoke/pco_usclib.spv')
        argv[argv.index('--depfile') + 1] = str(work / 'smoke/pco_usclib.d')
        argv.insert(argv.index('--') + 1, '-I' + str(reference / 'src/imagination'))
        discovery = list(argv)
        discovery[discovery.index('-o') + 1] = str(work / 'smoke/discovery.spv')
        discovery[discovery.index('--depfile') + 1] = str(work / 'smoke/discovery.d')
        clc_commands = [row for row in json.loads((build / 'compile_commands.json').read_text())
                        if (Path(row['directory']) / row['file']).resolve(strict=True) == source / 'src/compiler/clc/clc_helpers.cpp']
        require(clc_commands and '-DUSE_STATIC_OPENCL_C_H=1' in shlex.split(clc_commands[0]['command']),
                'Native CLC does not embed its OpenCL headers')
        virtual_headers = {str(work / 'tmp/openclon12' / name): str((build / 'src/compiler/clc' / (name + '.h')).resolve(strict=True))
                           for name in ('opencl-c-base.h', 'opencl-c.h')}
        input_hashes.update({path: sha(path) for path in virtual_headers.values()})
        compile_environment = {'TMPDIR': str(work / 'tmp')}
        run(discovery, 'common-discover', compile_environment)
        dependencies = shader_dependencies(work / 'smoke/discovery.d', build, virtual_headers)
        shader_hashes = {path: sha(path) for path in dependencies}
        run(argv, 'common-clc', compile_environment)
        require(shader_dependencies(work / 'smoke/pco_usclib.d', build, virtual_headers) == dependencies,
                'Common shader dependency set changed')
        require(all(sha(path) == digest for path, digest in shader_hashes.items()), 'Common shader dependency changed')
        write_json(work / 'shader-inputs.json', shader_hashes)
        run([validator, work / 'smoke/pco_usclib.spv'], 'common-validate')
        run([work / 'bin/vtn_bindgen2', work / 'smoke/pco_usclib.spv', work / 'smoke/pco_usclib.cpp', work / 'smoke/pco_usclib.h'], 'common-nir')
        outputs = ['pco_usclib.spv', 'pco_usclib.cpp', 'pco_usclib.h']
        if 'powervr' in profiles:
            run([work / 'bin/pco_clc', work / 'smoke/pco_usclib.spv', work / 'smoke/pco_uscgen_programs.h', work / 'smoke/pco_uscgen_programs.c'],
                'common-pco', {'PCO_DEBUG': 'no_pred_cf'})
            outputs += ['pco_uscgen_programs.h', 'pco_uscgen_programs.c']
        require(all((work / 'smoke' / path).stat().st_size > 0 for path in outputs), 'Empty generated output')
        input_hashes.update(shader_hashes)
        require(all(sha(path) == digest for path, digest in input_hashes.items()), 'Native build changed during sealing')
        require(all(sha(source / path) == digest for path, digest in source_hashes.items()), 'Native source changed during sealing')
        scope = 'Pinned native source and real compiled tools. Upstream common OpenCL to SPIR-V/NIR smoke.'
        if 'powervr' in profiles:
            scope += ' PowerVR PCO generation is checked.'
        if 'intel' in profiles:
            scope += ' Intel shader interfaces are bound; full Intel shader generation is a separate target build gate.'
        scope += ' No target execution.'
        write_json(work / 'receipt.json', dict(schema='ember-mesa-generators-1', mesa='26.2.5', llvm='23.1.4',
                   source=str(source), build=str(build), archive_sha256=MESA_SHA256, profiles=profiles,
                   host_prefix=str(prefix),
                   commands=commands, inputs=input_hashes, directory_inputs=directory_inputs,
                   virtual_headers=virtual_headers, scope=scope))
        (work / 'FORMAT').write_text('ember-mesa-generators-1\n')
        (work / 'PROFILES').write_text(','.join(profiles) + '\n')
        shutil.rmtree(reference)
        files = [path for path in sorted(work.rglob('*')) if path.is_file()]
        (work / 'installed.sha256').write_text(''.join(f'{sha(path)}  {path.relative_to(work)}\n' for path in files))
    print('PASS: sealed native Mesa 26.2.5 generators: ' + str(work))


if __name__ == '__main__':
    sdk_source.install_signal_handlers()
    try:
        require(sys.version_info[:2] == (3, 15), 'Host Python 3.15 is required')
        _, arguments = sdk_source.load_sdk()
        seal(arguments)
    except Exception as error:
        sdk_source.exit_error(error)
