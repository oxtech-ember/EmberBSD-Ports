#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import os
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '../../pkgsrc/lang/llvm/files'))
from sdk_source import load_sdk
from sysroot_archive import extract


def fetch_sysroot(revision, expected_manifest, work):
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import read_json, write_json
    from emberbsd_sdk.paths import canonical_existing, inside
    from emberbsd_sdk.process import run_logged
    from emberbsd_sdk.elf import read_elf_header

    def check(value, message):
        if not value:
            raise SDKError(message)

    check(re.fullmatch('[0-9a-f]{40}', revision) and re.fullmatch('[0-9a-f]{64}', expected_manifest) and os.path.isabs(work), 'Full source commit, manifest SHA256 and absolute unused work required')
    work = os.path.abspath(work)
    check(not os.path.lexists(work), 'Use a fresh work directory')
    os.mkdir(work, 0o700)
    downloads = work + '/downloads'
    os.mkdir(downloads)
    tag = 'build-' + revision + '-aarch64-sysroot'
    base = 'https://github.com/oxtech-ember/EmberBSD/releases/download/' + tag + '/'

    def fetch(name):
        check(re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]*', name), 'Unsafe asset name')
        path = downloads + '/' + name
        run_logged(['curl', '--fail', '--location', '--silent', '--show-error', '--proto', '=https', '--proto-redir', '=https', '--tlsv1.2', '--output', path, base + name], work + '/' + name + '.download.log')
        return path

    manifest_path = fetch('manifest.json')
    check(sha256_file(manifest_path) == expected_manifest, 'Pinned manifest SHA256 differs')
    manifest = read_json(manifest_path)
    schema = manifest.get('schema')
    modern = schema in ('emberbsd.aarch64.sysroot.v2', 'emberbsd.aarch64.sysroot.v3')
    check(schema in ('emberbsd.aarch64.sysroot.v1', 'emberbsd.aarch64.sysroot.v2', 'emberbsd.aarch64.sysroot.v3') and
          [manifest.get(k) for k in ('repository', 'source_commit', 'release_tag', 'architecture', 'machine')] ==
          ['oxtech-ember/EmberBSD', revision, tag, 'aarch64', 'evbarm'], 'Wrong source, schema or architecture')
    qualification = manifest['qualification']
    check(isinstance(qualification, dict) and qualification.get('source_commit') == revision, 'Published sysroot has no target qualification')
    required = ('libc_aliases', 'cross_c11', 'cross_cxx20', 'target_c11', 'target_cxx20', 'base_loader_smoke', 'fork_cas')
    check(all(qualification.get('checks', {}).get(name) is True for name in required), 'Incomplete target qualification')
    files = manifest['files']
    check(isinstance(files, list) and all(isinstance(file, dict) for file in files), 'Invalid file manifest')
    if modern:
        from emberbsd_sdk.os_release import require_qualification
        names = [file.get('name') for file in files]
        check(all(isinstance(name, str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]*', name) for name in names) and
              len(names) == len(set(names)), 'Invalid or duplicate asset name')
        check(all(isinstance(file.get('sha256'), str) and re.fullmatch('[0-9a-f]{64}', file['sha256']) and
                  type(file.get('size')) is int and 0 < file['size'] < 2**31 for file in files), 'Invalid asset hash or size')
        require_qualification(manifest, 'aarch64-sysroot')
    for name in ('base.tar.xz', 'comp.tar.xz', 'build-profile.json'):
        matches = [file for file in files if file.get('name') == name]
        check(len(matches) == 1, 'Missing or duplicate asset: ' + name)
        file = matches[0]
        check(isinstance(file['sha256'], str) and re.fullmatch('[0-9a-f]{64}', file['sha256']) and type(file['size']) is int and 0 < file['size'] < 2**31, 'Invalid asset hash or size')
        path = fetch(name)
        check(os.path.getsize(path) == file['size'] and sha256_file(path) == file['sha256'], 'Downloaded asset differs: ' + name)
    profile = read_json(downloads + '/build-profile.json')
    check(profile == manifest['build_profile'] and profile['source_commit'] == revision and profile['status'] == 'built' and profile['source_repository'] == 'https://github.com/oxtech-ember/EmberBSD', 'Build provenance differs')
    if modern:
        from emberbsd_sdk.os_release_builder import validate_profile
        check(type(profile.get('schema')) is int and profile['schema'] in
              ((2, 3) if schema == 'emberbsd.aarch64.sysroot.v2' else (4, 5)),
              'Manifest and build profile schema differ')
        validate_profile(profile, revision, 'aarch64')
        check(manifest.get('product_version') == profile['product_version'], 'Product version provenance differs')
        check(manifest.get('source_archive_sha256') == profile['source_sha256'], 'Source export provenance differs')
        kernel_digest = next(file['sha256'] for file in files if file['name'] == 'netbsd-EMBER64.gz')
        check(profile['output_sha256']['netbsd-EMBER64.gz'] == kernel_digest == qualification['kernel_gzip_sha256'],
              'Mixed kernel provenance: netbsd-EMBER64.gz')
    for part in ('base', 'comp'):
        name = part + '.tar.xz'
        digest = next(file['sha256'] for file in files if file['name'] == name)
        check(profile['output_sha256']['release/evbarm-aarch64/binary/sets/' + name] == digest and qualification[part + '_sha256'] == digest, 'Mixed set provenance: ' + name)
    root = work + '/sysroot'
    inventory = extract([downloads + '/' + name + '.tar.xz' for name in ('base', 'comp')], root)
    aliases = {}
    for name in ('lib/libc.so', 'lib/libc.so.12', 'usr/lib/libc.so', 'usr/lib/libc.so.12'):
        resolved = canonical_existing(root + '/' + name)
        check(inside(resolved, root), 'libc alias escapes sysroot')
        aliases[name] = dict(path=os.path.relpath(resolved, root), sha256=sha256_file(resolved))
    check(len({v['sha256'] for v in aliases.values()}) == 1, 'libc aliases resolve to different bytes')
    for name in ('usr/include/stdio.h', 'usr/include/pthread.h', 'usr/lib/crt0.o', 'usr/lib/crti.o', 'usr/lib/crtn.o', 'usr/lib/libc.a', 'usr/lib/libpthread.a'):
        check(os.path.isfile(root + '/' + name), 'Missing development input: ' + name)
    for path in (root + '/usr/lib/crt0.o', canonical_existing(root + '/lib/libc.so.12')):
        check(read_elf_header(path, machine=183), 'Wrong target ELF architecture')
    write_json(work + '/sysroot-files.json', inventory)
    write_json(work + '/receipt.json', dict(source_commit=revision, manifest_schema=schema, manifest_sha256=expected_manifest, release_url=base, libc_aliases=aliases, entries=len(inventory),
        links='Absolute archive symlinks are normalized to relative paths inside this target snapshot. Regular file bytes are unchanged.',
        scope='OS base/comp only. The selected cross compiler and application runtime are separate inputs.'))
    print('PASS: verified AArch64 OS sysroot at ' + root)


if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        _, args = load_sdk()
        if len(args) != 3:
            raise ValueError('Usage: fetch-sysroot.py --sdk-source SOURCE FULL_SOURCE_COMMIT MANIFEST_SHA256 /absolute/unused-work')
        fetch_sysroot(*args)
    except Exception as error:
        exit_error(error, prefix='Sysroot import stopped: ')
