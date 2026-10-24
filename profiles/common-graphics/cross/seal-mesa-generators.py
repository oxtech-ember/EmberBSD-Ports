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


def seal(arguments):
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
    from emberbsd_sdk.process import ContextLocks, sanitized_environment
    from emberbsd_sdk.stream import capture_streamed

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('intel', 'powervr', 'all'), default='powervr')
    parser.add_argument('archive')
    parser.add_argument('source')
    parser.add_argument('build')
    parser.add_argument('validator')
    parser.add_argument('work')
    args = parser.parse_args(arguments)
    values = [getattr(args, name) for name in ('archive', 'source', 'build', 'validator', 'work')]
    require(all(re.fullmatch(r'/[A-Za-z0-9_./-]+', value) for value in values),
            'Use absolute paths without whitespace or shell metacharacters')
    archive, source, build, validator = [Path(value).resolve(strict=True) for value in values[:4]]
    work = Path(os.path.abspath(args.work))
    require(not os.path.lexists(work), 'NEW_WORK must not exist')
    require(platform.system() == 'Darwin' and platform.machine() == 'arm64',
            'This native generator recipe requires macOS ARM64')
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
            env = sanitized_environment()
            env.update(TMPDIR=str(work / 'tmp'), TMP=str(work / 'tmp'), TEMP=str(work / 'tmp'))
            env.update(overrides)
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

        for name, path in tools.items():
            binary = build / path
            require(os.access(binary, os.X_OK), 'Missing real native tool: ' + str(binary))
            with binary.open('rb') as stream:
                require(stream.read(8) == struct.pack('<II', 0xfeedfacf, 0x0100000c), 'Expected native ARM64 Mach-O')
            dependencies = run(['otool', '-L', binary], name + '-dependencies')
            require(all(line.strip().startswith(('/usr/lib/', '/System/Library/'))
                        for line in dependencies.splitlines()[1:]), 'Unrecorded non-system shared dependency')
        require(os.access(validator, os.X_OK), 'Missing SPIR-V validator')
        inputs = [Path(__file__).resolve(), archive, validator, build / 'build.ninja', build / 'compile_commands.json']
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
        reference = work / 'reference'
        reference.mkdir()
        run(['tar', '-xf', archive, '--strip-components=1', '-C', reference], 'extract')
        bvnc_patch = PORTS / 'probes/a733-accelerators/host-tools/mesa-26.2.4-pco-bvnc.patch'
        pco = 'src/imagination/pco/uscgen/pco_clc.c'
        if sha(reference / pco) != sha(source / pco):
            run(['patch', '--no-backup-if-mismatch', '-f', '-N', '-F', '0', '-p1', '-d', reference, '-i', bvnc_patch], 'bvnc-patch')
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
        for name in ('meson-info.json', 'intro-projectinfo.json', 'intro-buildoptions.json', 'intro-targets.json', 'intro-dependencies.json'):
            shutil.copy2(metadata / name, work / 'metadata' / name)
        for name in ('build.ninja', 'compile_commands.json'):
            shutil.copy2(build / name, work / 'metadata' / name)
        interface_patch = PORTS / 'pkgsrc/graphics/MesaLib/patches/patch-src_imagination_common_pvr__iface.h'
        run(['patch', '--no-backup-if-mismatch', '-f', '-N', '-F', '0', '-p0', '-d', reference, '-i', interface_patch], 'interface-patch')
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
        input_hashes.update({str(path): sha(path) for path in (bvnc_patch, interface_patch)})
        scope = 'Pinned native source and real compiled tools. Upstream common OpenCL to SPIR-V/NIR smoke.'
        if 'powervr' in profiles:
            scope += ' PowerVR PCO generation is checked.'
        if 'intel' in profiles:
            scope += ' Intel shader interfaces are bound; full Intel shader generation is a separate target build gate.'
        scope += ' No target execution.'
        write_json(work / 'receipt.json', dict(schema='ember-mesa-generators-1', mesa='26.2.5', llvm='23.1.4',
                   source=str(source), build=str(build), archive_sha256=MESA_SHA256, profiles=profiles,
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
