#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Use pinned KiCad sources and SDK host API 1.
"""Build the actual KINNG causal controls; optionally run them on the target."""

import argparse
import importlib.util
import os
from pathlib import Path
import re
import shutil
import signal
import sys
import tarfile
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace

sys.dont_write_bytecode = True

ARCHIVE_SHA256 = '2fd6e4a0f6212fe0d26582be01e85c4d6fd59ce664018c0ffb94b2f1b074be51'
CPP_SHA256 = '02db25775b65a29db2d6c2c82649b0ce29f180fadb77d331f07b8450fe1a326e'
HEADER_SHA256 = 'b2f7bc21da91f0ff7df5c55ecce83aaad51fc5c922fe22536b6414077352668b'
CANDIDATE_SHA256 = '4f720dbea658ba1588a0ba79161567213f757284d0f8c4c7adbba0565c494387'
CPP = 'libs/kinng/src/kinng.cpp'
HEADER = 'libs/kinng/include/kinng.h'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_sdk(source):
    require(source and os.path.isabs(source), 'select an absolute SDK source')
    root = Path(source).resolve(strict=True)
    package = root / 'src/emberbsd_sdk'
    require((package / '__init__.py').is_file(), 'SDK source has no emberbsd_sdk API')
    sys.path.insert(0, str(root / 'src'))
    import emberbsd_sdk
    require(type(emberbsd_sdk.API_VERSION) is int and emberbsd_sdk.API_VERSION == 1 and
            Path(emberbsd_sdk.__file__).resolve().parent == package,
            'the selected SDK must provide API version 1')
    from emberbsd_sdk import stream
    from emberbsd_sdk.elf import read_elf_dynamic
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import read_json, write_json
    from emberbsd_sdk.paths import canonical_existing, canonical_new
    require(getattr(stream, 'PRODUCER_STREAM_API', None) == 1 and
            getattr(stream, 'PRODUCER_INSPECTION_API', None) == 1,
            'SDK needs producer stream and inspection API 1')
    return SimpleNamespace(root=str(root), capture=stream.capture_streamed,
        sha256=sha256_file, read_json=read_json, write_json=write_json,
        existing=canonical_existing, new=canonical_new, elf=read_elf_dynamic,
        CommandError=CommandError, ProcessOwnershipError=ProcessOwnershipError)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', default=os.environ.get('EMBERBSD_SDK_SOURCE'))
    parser.add_argument('--query-config', help='Run all eight cases through the production query runner')
    parser.add_argument('archive', metavar='KICAD_ARCHIVE')
    parser.add_argument('cxx', metavar='GCC16_CXX')
    parser.add_argument('sysroot', metavar='SYSROOT')
    parser.add_argument('new_work', metavar='NEW_WORK')
    args = parser.parse_args()
    require(sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 15),
            'select build-host CPython 3.15')
    sdk = load_sdk(args.sdk_source)
    here = Path(__file__).resolve().parent
    ports = here.parents[4]
    archive, cxx, sysroot = map(sdk.existing, (args.archive, args.cxx, args.sysroot))
    require(os.path.isabs(args.new_work), 'new work must be absolute')
    work = Path(sdk.new(args.new_work))
    require(not os.path.lexists(work), 'work already exists')
    require(not any(Path(value).is_relative_to(work) or work.is_relative_to(Path(value))
                    for value in (sysroot, sdk.root, str(ports))), 'input/output trees overlap')
    require(not Path(archive).is_relative_to(work), 'archive overlaps work')
    require(sdk.sha256(archive) == ARCHIVE_SHA256, 'KiCad archive SHA256 differs')
    work.mkdir(mode=0o700)
    (work / 'incomplete').write_text('This work is not an accepted build.\n', encoding='ascii')
    os.environ.update(TMPDIR=str(work), TMP=str(work), TEMP=str(work))
    tempfile.tempdir = str(work)
    env = dict(os.environ, TMPDIR=str(work), TMP=str(work), TEMP=str(work),
               EMBERBSD_SDK_SOURCE=sdk.root, PYTHONDONTWRITEBYTECODE='1')
    commands = []

    def command(name, argv):
        status = 0
        try:
            result = sdk.capture(argv, cwd=str(work), env=env, timeout=120,
                                 empty_snapshot_timeout=10)
            stdout, stderr = result.value, result.stderr
            require(not result.stderr_truncated, 'producer stderr was truncated')
        except sdk.CommandError as error:
            status, stdout, stderr = error.returncode, error.stdout, error.stderr
        (work / (name + '.stdout')).write_bytes(stdout)
        (work / (name + '.stderr')).write_bytes(stderr)
        commands.append(dict(name=name, argv=argv, status=status))
        require(status == 0, f'{name} failed: inspect {work}')
        return stdout.decode('utf-8', 'strict').strip()

    try:
        version = command('gcc-version', [cxx, '-dumpfullversion'])
        triplet = command('gcc-target', [cxx, '-dumpmachine'])
        require(re.fullmatch(r'16\.[0-9]+\.[0-9]+', version) and
                triplet in ('aarch64--netbsd', 'x86_64--netbsd'), 'select common GCC16')
        machine = 183 if triplet == 'aarch64--netbsd' else 62
        runtime = Path(sysroot) / 'usr/pkg/gcc16/lib'
        support = runtime / 'gcc' / triplet / version
        require((support / 'libgcc.a').is_file(), 'selected GCC16 runtime is missing')
        wanted = {CPP, HEADER, 'LICENSE', 'LICENSE.GPLv3', 'AUTHORS.txt'}
        found = set()
        with tarfile.open(archive, 'r|bz2') as stream:
            for member in stream:
                relative = member.name.removeprefix('kicad-10.0.7/')
                if relative not in wanted:
                    continue
                require(relative not in found and member.isfile() and member.size < 1024 * 1024,
                        'invalid or duplicate selected KiCad archive member')
                data = stream.extractfile(member).read()
                target = work / 'upstream' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                found.add(relative)
        require(found == wanted and sdk.sha256(archive) == ARCHIVE_SHA256,
                'selected source is missing or archive changed')
        require(sdk.sha256(str(work / 'upstream' / CPP)) == CPP_SHA256 and
                sdk.sha256(str(work / 'upstream' / HEADER)) == HEADER_SHA256,
                'selected upstream source/header hashes differ')
        shutil.copytree(work / 'upstream', work / 'candidate')
        shutil.copytree(work / 'upstream', work / 'recipe')
        command('source-patch', ['patch', '-f', '-F', '0', '-p1', '-d', str(work / 'candidate'),
            '-i', str(here.parents[1] / 'patches/kinng-lifecycle.patch')])
        recipe_patch = ports / 'pkgsrc/cad/kicad10/patches/patch-libs_kinng_src_kinng.cpp'
        command('recipe-patch', ['patch', '-f', '-F', '0', '-p0', '-d', str(work / 'recipe'),
                                '-i', str(recipe_patch)])
        require(sdk.sha256(str(work / 'candidate' / CPP)) == CANDIDATE_SHA256 and
                sdk.sha256(str(work / 'recipe' / CPP)) == CANDIDATE_SHA256,
                'p0/p1 patch outputs differ from the executed candidate')
        for tree in ('candidate', 'recipe'):
            require(sdk.sha256(str(work / tree / HEADER)) == HEADER_SHA256,
                    'the real class header changed')
        flags = [f'--sysroot={sysroot}', '-B' + str(support) + '/', '-std=c++20',
                 '-O2', '-g', '-Wall', '-Wextra', '-pthread',
                 '-fsanitize=undefined', '-fsanitize-undefined-trap-on-error',
                 '-fno-sanitize-recover=all', '-I' + sysroot + '/usr/pkg/include',
                 '-I' + str(here / 'unit-only-wx-log-adapter')]
        links = ['-L' + sysroot + '/usr/pkg/lib', '-L' + str(runtime),
                 '-Wl,-rpath,/usr/pkg/lib:/usr/pkg/gcc16/lib',
                 *['-Wl,-rpath-link,' + sysroot + '/' + p for p in
                   ('lib', 'usr/lib', 'usr/pkg/gcc16/lib')],
                 *['-Wl,--wrap=' + name for name in
                   ('nng_rep0_open', 'nng_close', 'nng_listener_start', 'nng_recv', 'nng_free')],
                 '-lnng']
        outputs = {}
        for tree in ('upstream', 'candidate'):
            binary = work / ('kinng-' + tree + '-ubsan')
            command('build-' + tree, [cxx, *flags, '-I' + str(work / tree / 'libs/kinng/include'),
                str(work / tree / CPP), str(here / 'kinng-lifecycle-unit.cpp'), *links, '-o', str(binary)])
            dynamic = sdk.elf(str(binary), machine=machine)
            require('libnng.so.1' in dynamic['needed'] and
                    not any('ubsan' in name for name in dynamic['needed']),
                    'target provider or trap-mode dependency differs')
            outputs[tree] = dict(path=str(binary), sha256=sdk.sha256(str(binary)), elf=dynamic)
        results = {}
        if args.query_config:
            config_path = sdk.existing(args.query_config)
            config = sdk.read_json(config_path)
            require(isinstance(config, dict), 'query configuration must be an object')
            require(sdk.existing(config['sysroot']) == sysroot and
                    config.get('target', 'aarch64') == ('aarch64' if machine == 183 else 'amd64'),
                    'query configuration differs from the selected target/sysroot')
            require(work.is_relative_to(Path(sdk.existing(config['build_root']))),
                    'work is outside the configured query build root')
            cache = Path(sdk.existing(config['cache']))
            helper = ports / 'pkgsrc/devel/gobject-introspection/files/target-query.py'
            sys.path.insert(0, str(helper.parent))
            spec = importlib.util.spec_from_file_location('kinng_production_query', helper)
            query = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(query)
            # Reuse the production implementation and its owned producer cleanup.
            # Do not nest an unowned controller subprocess around the query runner.
            os.environ['EMBERBSD_SDK_SOURCE'] = sdk.root
            os.environ['EMBERBSD_GI_QUERY_CONFIG'] = config_path
            os.environ['EMBERBSD_GI_FAILURE_MARKER'] = str(work / 'query-failure')
            for tree in ('upstream', 'candidate'):
                for case in ('ownership', 'stop', 'create-error', 'start-error'):
                    name = tree + '-' + case
                    before = set(cache.glob('gi-query-*'))
                    with open(work / (name + '.stdout'), 'w') as stdout, open(work / (name + '.stderr'), 'w') as stderr:
                        with redirect_stdout(stdout), redirect_stderr(stderr):
                            status = query.query(['--execute', outputs[tree]['path'], case])
                    stdout, stderr = (work / (name + '.stdout')).read_bytes(), (work / (name + '.stderr')).read_bytes()
                    expected = 0 if tree == 'candidate' else 124 if case == 'stop' else 1
                    require(status == expected and not stderr, f'{name} target result differs')
                    if case == 'ownership':
                        count = '0' if tree == 'candidate' else '16'
                        require(f'real_server_allocations=16 outstanding={count} closes=1\n'.encode() == stdout,
                                'allocation witness differs')
                    if case == 'stop':
                        marker = b'STOP_RETURNED_WITHOUT_REPLY\n' if tree == 'candidate' else b'STOP_SUBPROCESS_DEADLINE\n'
                        require(b'STOP_ENTERED_AFTER_REAL_RECEIVE\n' in stdout and marker in stdout,
                                'missing causal stop marker')
                    if case == 'create-error':
                        closed = 1 if tree == 'candidate' else 0
                        require(stdout == f'listener_create closes={closed} receive_calls=0\n'.encode(),
                                'listener-create ownership witness differs')
                    if case == 'start-error':
                        calls = 0 if tree == 'candidate' else 1
                        require(stdout == f'listener_start closes=1 receive_calls={calls}\n'.encode(),
                                'injected listener-start witness differs')
                    entry = f"{outputs[tree]['sha256']}  {outputs[tree]['path']}"
                    receipts = [p for p in set(cache.glob('gi-query-*')) - before
                        if (p / 'sources.sha256').is_file() and entry in (p / 'sources.sha256').read_text().splitlines()]
                    require(len(receipts) == 1, 'missing or ambiguous provider receipt')
                    receipt = receipts[0]
                    require((receipt / 'cleanup.log').read_bytes().startswith(b'0\n') and
                            not os.path.lexists(receipt / 'stage') and
                            not os.path.lexists(receipt / 'input.tar.gz'), 'target cleanup failed')
                    results[name] = dict(status=status, stdout=stdout.decode(), stderr=stderr.decode(),
                                         provider_receipt=str(receipt))
        require(not (work / 'query-failure').exists(), 'target infrastructure failure marker survived')
        sdk.write_json(str(work / 'receipt.json'), dict(archive_sha256=ARCHIVE_SHA256,
            sdk_source=sdk.root, sdk_api=1,
            sdk_modules_sha256={str(p.relative_to(Path(sdk.root))): sdk.sha256(str(p))
                for p in sorted((Path(sdk.root) / 'src/emberbsd_sdk').glob('*.py'))},
            cli_sha256=sdk.sha256(str(Path(__file__).resolve())),
            python=str(Path(sys.executable).resolve()),
            python_version=sys.version, python_sha256=sdk.sha256(str(Path(sys.executable).resolve())),
            cxx=cxx, cxx_sha256=sdk.sha256(cxx), gcc_version=version,
            triplet=triplet, commands=commands, outputs=outputs,
            source_sha256=CPP_SHA256, candidate_sha256=CANDIDATE_SHA256, header_sha256=HEADER_SHA256,
            harness_sha256=sdk.sha256(str(here / 'kinng-lifecycle-unit.cpp')),
            source_patch_sha256=sdk.sha256(str(here.parents[1] / 'patches/kinng-lifecycle.patch')),
            recipe_patch_sha256=sdk.sha256(str(recipe_patch)), target_results=results,
            target_execution='passed-eight-causal-cases' if results else 'not-requested',
            boundary='Actual class plus logging adapter and consumer UBSan trap only; no full KiCad, real wx, Memcheck or instrumented dependency acceptance.'))
        (work / 'incomplete').unlink()
        print('PASS: pinned p0/p1 source equality, GCC16 builds' + (' and eight target causal cases' if results else ' (target execution not requested)'))
    except sdk.ProcessOwnershipError:
        (work / 'producer-ownership-unconfirmed').write_text('Retain and quarantine this work.\n', encoding='ascii')
        raise


if __name__ == '__main__':
    def interrupted(number, _frame):
        raise SystemExit(128 + number)
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, interrupted)
    try:
        main()
    except Exception as error:
        print(f'error: {error}', file=sys.stderr)
        raise SystemExit(1)
