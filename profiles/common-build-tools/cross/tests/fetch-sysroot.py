#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Real CLI, local HTTPS client fixture.
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / '../../pkgsrc/lang/llvm/files'))
from sdk_source import load_sdk
sdk, args = load_sdk()


def write_json(path, value):
    path.write_text(json.dumps(value) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(root, name):
    path = root / name
    return dict(name=name, size=path.stat().st_size, sha256=digest(path))


def pack(source, output):
    with tarfile.open(output, 'w:xz', format=tarfile.USTAR_FORMAT) as archive:
        archive.add(source, arcname='.')


with tempfile.TemporaryDirectory(prefix='ember-fetch-sysroot-') as temporary:
    root = Path(temporary)
    base, comp, template, commands = [root / p for p in ('base', 'comp', 'template', 'commands')]
    for p in (base / 'lib', base / 'usr/lib', comp / 'usr/lib', comp / 'usr/include', template, commands):
        p.mkdir(parents=True)
    elf = bytearray(64)
    elf[:7] = b'\x7fELF\x02\x01\x01'
    elf[18:20] = (183).to_bytes(2, 'little')
    elf[20:24] = (1).to_bytes(4, 'little')
    elf[52:54] = (64).to_bytes(2, 'little')
    (base / 'lib/libc.so.12.229').write_bytes(elf)
    for name, target in {'lib/libc.so.12': 'libc.so.12.229', 'lib/libc.so': 'libc.so.12', 'usr/lib/libc.so.12': '/lib/libc.so.12', 'usr/lib/libc.so': '/lib/libc.so'}.items():
        (base / name).symlink_to(target)
    for name in ('stdio.h', 'pthread.h'):
        (comp / 'usr/include' / name).write_text('/* fixture */\n')
    for name in ('crt0.o', 'crti.o', 'crtn.o'):
        (comp / 'usr/lib' / name).write_bytes(elf)
    for name in ('libc.a', 'libpthread.a'):
        (comp / 'usr/lib' / name).write_bytes(b'!<arch>\n')
    for name, source in [('base', base), ('comp', comp)]:
        pack(source, template / (name + '.tar.xz'))
    revision = 'a' * 40
    tag = 'build-' + revision + '-aarch64-sysroot'
    prefix = 'https://github.com/oxtech-ember/EmberBSD/releases/download/' + tag + '/'
    hashes = {name: digest(template / (name + '.tar.xz')) for name in ('base', 'comp')}
    profile = dict(status='built', source_commit=revision, source_repository='https://github.com/oxtech-ember/EmberBSD',
        output_sha256={'release/evbarm-aarch64/binary/sets/' + name + '.tar.xz': sha for name, sha in hashes.items()})
    write_json(template / 'build-profile.json', profile)
    checks = ('libc_aliases', 'cross_c11', 'cross_cxx20', 'target_c11', 'target_cxx20', 'base_loader_smoke', 'fork_cas')
    manifest = dict(schema='emberbsd.aarch64.sysroot.v1', repository='oxtech-ember/EmberBSD', source_commit=revision,
        release_tag=tag, architecture='aarch64', machine='evbarm', qualification=dict(source_commit=revision, checks=dict.fromkeys(checks, True),
        base_sha256=hashes['base'], comp_sha256=hashes['comp']), build_profile=profile,
        files=[record(template, name) for name in ('base.tar.xz', 'comp.tar.xz', 'build-profile.json')])
    write_json(template / 'manifest.json', manifest)
    curl = commands / 'curl'
    curl.write_text(f'''#!{sys.executable}
import os, pathlib, shutil, sys
expected = ['--fail','--location','--silent','--show-error','--proto','=https','--proto-redir','=https','--tlsv1.2','--output']
assert sys.argv[1:-2] == expected
path, url = sys.argv[-2:]
prefix = os.environ['FIXTURE_PREFIX']
assert url.startswith(prefix)
name = url[len(prefix):]
assert name in ('manifest.json','base.tar.xz','comp.tar.xz','build-profile.json')
assert path == os.environ['FIXTURE_WORK'] + '/downloads/' + name
with open(os.environ['FIXTURE_CALLS'], 'a') as output: output.write(name + '\\n')
shutil.copyfile(pathlib.Path(os.environ['FIXTURE_SERVED']) / name, path)
''')
    curl.chmod(0o755)
    calls = root / 'calls'

    def invoke(served, work, pin):
        calls.write_text('')
        env = dict(os.environ, PATH=str(commands) + ':' + os.environ['PATH'], FIXTURE_PREFIX=prefix, FIXTURE_WORK=str(work), FIXTURE_CALLS=str(calls), FIXTURE_SERVED=str(served), PYTHONDONTWRITEBYTECODE='1')
        return subprocess.run([sys.executable, '-B', str(HERE / 'fetch-sysroot.py'), '--sdk-source', sdk, revision, pin, str(work)], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    accepted = root / 'accepted'
    result = invoke(template, accepted, digest(template / 'manifest.json'))
    assert result.returncode == 0, result.stdout
    assert calls.read_text().splitlines() == ['manifest.json', 'base.tar.xz', 'comp.tar.xz', 'build-profile.json']
    receipt = (accepted / 'receipt.json').read_bytes()
    assert (accepted / 'sysroot/usr/lib/libc.so').read_bytes() == elf
    cases = ['wrong-pin', 'changed-set', 'manifest-source', 'profile-source', 'qualification-source', 'qualification-set', 'profile-set', 'missing-check', 'duplicate-asset', 'wrong-architecture', 'wrong-elf']
    for label in cases:
        served = root / label
        shutil.copytree(template, served)
        m = copy.deepcopy(manifest)
        p = copy.deepcopy(profile)
        expected = None
        if label == 'changed-set':
            with (served / 'base.tar.xz').open('ab') as out:
                out.write(b'changed')
            expected = 'Downloaded asset differs'
        elif label == 'manifest-source':
            m['source_commit'] = 'b' * 40
            expected = 'Wrong source'
        elif label == 'profile-source':
            p['source_commit'] = 'b' * 40
            expected = 'Build provenance differs'
        elif label == 'qualification-source':
            m['qualification']['source_commit'] = 'b' * 40
            expected = 'qualification'
        elif label == 'qualification-set':
            m['qualification']['comp_sha256'] = '0' * 64
            expected = 'Mixed set provenance'
        elif label == 'profile-set':
            p['output_sha256']['release/evbarm-aarch64/binary/sets/base.tar.xz'] = '0' * 64
            expected = 'Mixed set provenance'
        elif label == 'missing-check':
            del m['qualification']['checks']['target_cxx20']
            expected = 'Incomplete target qualification'
        elif label == 'duplicate-asset':
            m['files'].append(copy.deepcopy(m['files'][0]))
            expected = 'Missing or duplicate asset'
        elif label == 'wrong-architecture':
            m['architecture'] = 'amd64'
            expected = 'Wrong source'
        elif label == 'wrong-elf':
            wrong = root / 'wrong-elf-source'
            shutil.copytree(comp, wrong)
            damaged = bytearray(elf)
            damaged[18:20] = (62).to_bytes(2, 'little')
            (wrong / 'usr/lib/crt0.o').write_bytes(damaged)
            pack(wrong, served / 'comp.tar.xz')
            sha = digest(served / 'comp.tar.xz')
            p['output_sha256']['release/evbarm-aarch64/binary/sets/comp.tar.xz'] = sha
            m['qualification']['comp_sha256'] = sha
            m['files'] = [record(served, 'comp.tar.xz') if f['name'] == 'comp.tar.xz' else f for f in m['files']]
            expected = 'target header'
        if p != profile:
            write_json(served / 'build-profile.json', p)
            m['build_profile'] = p
            m['files'] = [record(served, 'build-profile.json') if f['name'] == 'build-profile.json' else f for f in m['files']]
        write_json(served / 'manifest.json', m)
        pin = '0' * 64 if label == 'wrong-pin' else digest(served / 'manifest.json')
        expected = expected or 'Pinned manifest SHA256 differs'
        result = invoke(served, root / ('rejected-' + label), pin)
        assert result.returncode and expected in result.stdout, label + ': ' + result.stdout
    result = invoke(template, accepted, digest(template / 'manifest.json'))
    assert result.returncode and 'fresh work directory' in result.stdout and not calls.read_text()
    assert (accepted / 'receipt.json').read_bytes() == receipt
    # Fresh schema-1 kits derive the version from source, without a command
    # override. Import preserves its original source/hash/qualification rules.
    source_version = root / 'source-version-v1'
    shutil.copytree(template, source_version)
    v1_manifest = copy.deepcopy(manifest)
    v1_profile = copy.deepcopy(profile)
    v1_profile.update(schema=1, commands=[['sh', './build.sh', 'tools'], ['sh', './build.sh', 'sets']])
    v1_manifest.update(product_version='2.7+dev', build_profile=v1_profile)
    write_json(source_version / 'build-profile.json', v1_profile)
    v1_manifest['files'] = [record(source_version, 'build-profile.json') if f['name'] == 'build-profile.json' else f for f in v1_manifest['files']]
    write_json(source_version / 'manifest.json', v1_manifest)
    result = invoke(source_version, root / 'accepted-source-version-v1', digest(source_version / 'manifest.json'))
    assert result.returncode == 0, result.stdout

    # Schema 2 delegates its build-receipt contract to the selected SDK. Construct
    # synthetic provenance and real archives; no compiler or target is executed.
    modern_profile = json.loads((HERE / 'tests/fetch-sysroot-v2-profile.json').read_text())
    revision = modern_profile['source_commit']
    tag = 'build-' + revision + '-aarch64-sysroot'
    prefix = 'https://github.com/oxtech-ember/EmberBSD/releases/download/' + tag + '/'
    outputs = dict(profile['output_sha256'], **{'netbsd-EMBER64.gz': 'f' * 64})
    modern_profile['output_sha256'] = outputs
    modern_profile['sdk_receipt']['outputs'] = copy.deepcopy(outputs)
    modern_manifest = copy.deepcopy(manifest)
    modern_manifest.update(schema='emberbsd.aarch64.sysroot.v2', source_commit=revision, release_tag=tag, product_version=modern_profile['product_version'], source_archive_sha256=modern_profile['source_sha256'], build_profile=modern_profile)
    modern_manifest['qualification']['source_commit'] = revision
    modern_manifest['files'] += [dict(name='netbsd-EMBER64.gz', size=64, sha256='f' * 64),
                                 dict(name='target-acceptance.log', size=64, sha256='e' * 64)]
    modern_manifest['qualification'].update(kernel_gzip_sha256='f' * 64, consumer_compiler='fixture GCC 16.2.0',
        execution='EmberBSD aarch64 full-system QEMU TCG', evidence_sha256={'target-acceptance.log': 'e' * 64})
    modern_cases = ['accepted-v2', 'v2-profile-schema', 'v2-compiler', 'v2-runtime', 'v2-command', 'v2-source-export',
                    'v2-qualification-evidence', 'v2-qualification-kernel', 'v2-qualification-platform',
                    'v2-missing-check', 'v2-changed-set', 'v2-manifest-pin', 'v2-profile-set', 'v2-source', 'unknown-schema', 'v2-profile-kernel', 'v2-product-version']
    for label in modern_cases:
        served = root / label
        shutil.copytree(template, served)
        m, p = copy.deepcopy(modern_manifest), copy.deepcopy(modern_profile)
        if label == 'v2-profile-schema': p['schema'] = 1
        elif label == 'v2-compiler': p['sdk_receipt']['signature']['compiler']['version'] = '12.5.0'
        elif label == 'v2-runtime': p['sdk_receipt']['signature']['runtime']['report']['metadata']['GCC_RUNTIME_TRIPLET'] = 'x86_64--netbsd'
        elif label == 'v2-command': p['commands'][0].append('NOCHECKFLIST=yes')
        elif label == 'v2-source-export': m['source_archive_sha256'] = '0' * 64
        elif label == 'v2-qualification-evidence': m['qualification']['evidence_sha256']['target-acceptance.log'] = '0' * 64
        elif label == 'v2-qualification-kernel': m['qualification']['kernel_gzip_sha256'] = '0' * 64
        elif label == 'v2-qualification-platform': m['qualification']['execution'] = 'host fixture'
        elif label == 'v2-missing-check': del m['qualification']['checks']['target_cxx20']
        elif label == 'v2-profile-set': p['output_sha256']['release/evbarm-aarch64/binary/sets/base.tar.xz'] = '0' * 64
        elif label == 'v2-product-version': m['product_version'] = '3.0'
        elif label == 'v2-profile-kernel':
            p['output_sha256']['netbsd-EMBER64.gz'] = '0' * 64
            p['sdk_receipt']['outputs']['netbsd-EMBER64.gz'] = '0' * 64
        elif label == 'v2-source': m['repository'] = 'foreign/OS'
        elif label == 'unknown-schema': m['schema'] = 'emberbsd.aarch64.sysroot.v4'
        elif label == 'v2-changed-set':
            with (served / 'base.tar.xz').open('ab') as out: out.write(b'changed')
        write_json(served / 'build-profile.json', p)
        m['build_profile'] = p
        m['files'] = [record(served, 'build-profile.json') if f['name'] == 'build-profile.json' else f for f in m['files']]
        write_json(served / 'manifest.json', m)
        pin = '0' * 64 if label == 'v2-manifest-pin' else digest(served / 'manifest.json')
        work = root / ('import-' + label)
        result = invoke(served, work, pin)
        if label == 'accepted-v2':
            assert result.returncode == 0, label + ': ' + result.stdout
            assert (work / 'sysroot/usr/lib/libc.so').read_bytes() == elf
            assert json.loads((work / 'receipt.json').read_text())['manifest_schema'] == 'emberbsd.aarch64.sysroot.v2'
        else:
            reason = {
                'v2-profile-schema': 'Manifest and build profile schema differ',
                'v2-compiler': 'Unverified common GCC16 compiler',
                'v2-runtime': 'Mixed GCC16 runtime receipt',
                'v2-command': 'Build command does not select the exact required profile',
                'v2-source-export': 'Source export provenance differs',
                'v2-qualification-evidence': 'Qualification lacks bound target evidence',
                'v2-qualification-kernel': 'Qualification has another netbsd-EMBER64.gz',
                'v2-qualification-platform': 'Unrecorded target execution platform',
                'v2-missing-check': 'Incomplete target qualification',
                'v2-changed-set': 'Downloaded asset differs',
                'v2-manifest-pin': 'Pinned manifest SHA256 differs',
                'v2-profile-set': 'Mixed output receipts',
                'v2-product-version': 'Product version provenance differs',
                'v2-profile-kernel': 'Mixed kernel provenance',
                'v2-source': 'Wrong source',
                'unknown-schema': 'Wrong source',
            }[label]
            assert result.returncode and reason in result.stdout and not (work / 'receipt.json').exists(), label + ': ' + result.stdout
    # Real SDK validators consume frozen synthetic profile data: no compiler or VM.
    profiles = json.loads((HERE / 'tests/fetch-sysroot-v3-profiles.json').read_text())
    for original in profiles:
        revision = original['source_commit']
        tag = 'build-' + revision + '-aarch64-sysroot'
        prefix = 'https://github.com/oxtech-ember/EmberBSD/releases/download/' + tag + '/'
        for label in ('valid', 'outer', 'profile', 'runtime', 'compiler', 'set', 'kernel', 'missing', 'corpus'):
            served = root / ('v3-' + str(original['schema']) + '-' + label)
            shutil.copytree(template, served)
            p = copy.deepcopy(original)
            p['output_sha256'].update(profile['output_sha256'])
            p['output_sha256']['netbsd-EMBER64.gz'] = 'f' * 64
            p['sdk_receipt']['outputs'] = copy.deepcopy(p['output_sha256'])
            m = copy.deepcopy(modern_manifest)
            m.update(schema='emberbsd.aarch64.sysroot.v3', source_commit=revision,
                     release_tag=tag, source_archive_sha256=p['source_sha256'], build_profile=p)
            q = m['qualification']
            q.update(source_commit=revision, consumer_compiler_family='clang',
                     consumer_compiler='fixture clang version 23.1.4', corpus='target-runtime-v2',
                     os_test_source_commit=revision, ports_source_commit='b' * 40,
                     test_source_inventory_sha256='c' * 64)
            q['checks'].update(libm_valid=True, setjmp_valid=True)
            if label == 'outer': m['schema'] = 'emberbsd.aarch64.sysroot.v2'
            elif label == 'profile': p['schema'] = 2
            elif label == 'runtime': p['sdk_receipt']['signature']['runtime']['manifest']['llvm_version'] = '22.1.0'
            elif label == 'compiler': q['consumer_compiler'] = 'fixture clang version 22.1.0'
            elif label == 'set': q['base_sha256'] = '0' * 64
            elif label == 'kernel': q['kernel_gzip_sha256'] = '0' * 64
            elif label == 'missing': del q['checks']['setjmp_valid']
            elif label == 'corpus': del q['test_source_inventory_sha256']
            write_json(served / 'build-profile.json', p)
            m['files'] = [record(served, 'build-profile.json') if f['name'] == 'build-profile.json' else f for f in m['files']]
            write_json(served / 'manifest.json', m)
            work = root / ('import-v3-' + str(original['schema']) + '-' + label)
            result = invoke(served, work, digest(served / 'manifest.json'))
            if label == 'valid':
                assert result.returncode == 0, label + ': ' + result.stdout
                assert json.loads((work / 'receipt.json').read_text())['manifest_schema'] == 'emberbsd.aarch64.sysroot.v3'
            else:
                assert result.returncode and not (work / 'receipt.json').exists(), label + ': ' + result.stdout
print('PASS: v1/v2/v3 importer CLI fixtures; HTTPS and target execution remain outside the fixture')
