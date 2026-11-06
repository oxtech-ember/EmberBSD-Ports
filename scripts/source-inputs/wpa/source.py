#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare and verify the pinned common pkgsrc wpa_supplicant source."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import sys
import tempfile

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
PACKAGE = 'net/wpa_supplicant'
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source
sys.path.append(str(PORTS / 'scripts'))
import prepared_receipt


def load_sdk(argv):
    sdk, argv = sdk_source.load_sdk(argv)
    globals()['SDK_SOURCE'] = sdk
    from emberbsd_sdk import jsonio, paths, process, sourceprep
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.publication import publish_directory_noreplace
    if getattr(sourceprep, 'PREPARED_TREE_API', None) != 1:
        raise SDKError('selected SDK lacks the prepared source tree API')
    globals().update(jsonio=jsonio, paths=paths, process=process, sourceprep=sourceprep,
                     SDKError=SDKError, publish_directory_noreplace=publish_directory_noreplace)
    return argv


def require(condition, message):
    if not condition:
        raise SDKError(message)


def read(path):
    handle, before = paths.open_regular(path)
    with handle:
        data = handle.read()
    paths.verify_stable(path, before)
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity_module():
    module_path = PORTS / 'scripts/pkgsrc-source-identity.py'
    spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_effective_identity(git):
    return identity_module().git_package_identity(PORTS, PACKAGE, git)


def source_identity(git):
    module = identity_module()
    return {'export': module.identity(PORTS, PACKAGE, git, SDK_SOURCE),
            'owner_sha256': digest(read(Path(__file__).resolve()))}


def recipe(exported):
    recipe_root = Path(exported) / PACKAGE
    makefile = read(recipe_root / 'Makefile')
    require(re.search(rb'^\.include[ \t]+"../../net/wpa_supplicant/Makefile\.common"[ \t]*$', makefile, re.M),
            'WPA recipe must include its common release inputs')
    common = read(recipe_root / 'Makefile.common')
    matches = re.findall(rb'^WPA_SUPPLICANT_VERSION[ \t]*([:?+!]?)=[ \t]*(.*)$', common, re.M)
    require(len(matches) == 1 and matches[0][0] == b'' and
            re.fullmatch(rb'[0-9]+(?:\.[0-9]+){1,2}', matches[0][1]),
            'ambiguous wpa_supplicant release')
    version = matches[0][1].decode('ascii')
    distnames = re.findall(rb'^DISTNAME[ \t]*([:?+!]?)=[ \t]*(.*)$', common, re.M)
    require(distnames == [(b'', b'wpa_supplicant-${WPA_SUPPLICANT_VERSION}')],
            'WPA recipe must use the common release version')
    distname = 'wpa_supplicant-' + version
    archive = distname + '.tar.gz'
    hostapd = 'hostapd-' + version + '.tar.gz'
    expected_distfiles = '${DISTNAME}${EXTRACT_SUFX} hostapd-${WPA_SUPPLICANT_VERSION}${EXTRACT_SUFX}'
    distfiles = re.findall(rb'^DISTFILES[ \t]*([:?+!]?)=[ \t]*(.*)$', common, re.M)
    require(len(distfiles) == 1 and distfiles[0][0] == b'' and
            distfiles[0][1].decode('ascii') == expected_distfiles,
            'WPA recipe must select both matching upstream archives')
    info = read(recipe_root / 'distinfo').decode('utf-8')
    archives = {}
    for filename in (archive, hostapd):
        hashes = {}
        for label, key in (('SHA512', 'sha512'), ('BLAKE2s', 'blake2s'), ('Size', 'size')):
            values = re.findall(r'^' + label + r' \(' + re.escape(filename) + r'\) = (\S+)(?: bytes)?$', info, re.M)
            require(len(values) == 1, 'ambiguous wpa archive ' + label)
            hashes[key] = int(values[0]) if key == 'size' else values[0]
        archives[filename] = hashes
    declared = re.findall(r'^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$', info, re.M)
    patches = sorted((recipe_root / 'patches').glob('patch-*'))
    require([p.name for p in patches] == sorted(name for name, _ in declared),
            'wpa_supplicant patch inventory differs from distinfo')
    for name, expected in declared:
        data = read(recipe_root / 'patches' / name)
        filtered = b''.join(line for line in data.splitlines(keepends=True) if b'$NetBSD' not in line)
        require(hashlib.sha1(filtered).hexdigest() == expected, 'wpa_supplicant patch checksum differs: ' + name)
    inputs = [recipe_root / 'Makefile', recipe_root / 'Makefile.common',
              recipe_root / 'distinfo', *patches]
    identity = dict(distname=distname, archive=archive, hostapd=hostapd, archives=archives,
                    recipe={str(path.relative_to(recipe_root)): digest(read(path)) for path in inputs})
    return identity, patches


def verify(source, git, archive=None, hostapd_archive=None, patch=None, pkgsrc_export=None, export_patch=None):
    record = jsonio.read_json(str(Path(source) / sourceprep.PREPARED_TREE_RECEIPT))
    old = record.get('identity') if isinstance(record, dict) else None
    record = sourceprep.validate_prepared_tree(source, package=PACKAGE, identity=old)
    prepared_receipt.require_current_identity(old, PACKAGE)

    # A current Git receipt proves the selected package inputs directly.
    # Do not make that scoped path depend on unrelated shared-export inputs.
    selector = identity_module()
    if isinstance(old, dict) and set(old) == {'effective', 'owner_sha256'}:
        owner_sha = digest(read(Path(__file__).resolve()))
        if (old.get('owner_sha256') == owner_sha and
                selector.current_git_package(old, old['owner_sha256'],
                                             lambda: git_effective_identity(git))):
            return record

    # Changed inputs need the shared export to compare or rebuild.
    shared = (selector.shared_export(pkgsrc_export, PORTS, git, SDK_SOURCE, export_patch or patch)
              if pkgsrc_export else None)
    identity = source_identity(git)
    if identity_module().current_git_package(old, identity['owner_sha256'], lambda: git_effective_identity(git)):
        # The receipt names the Git objects of the current effective recipe.
        require(identity == source_identity(git), 'pkgsrc export inputs changed during verification')
        return record
    require(patch and os.path.isabs(patch), 'effective wpa_supplicant verification requires an explicit patch')
    with tempfile.TemporaryDirectory(prefix='.wpa_supplicant-verify-') as tmp:
        selector = identity_module()
        if pkgsrc_export:
            # The run's single export, bound to the current Ports inputs.
            exported = shared
        else:
            exported = Path(tmp) / 'pkgsrc'
            process.capture([sys.executable, '-B', str(PORTS / 'scripts/prepare-pkgsrc.py'),
                             str(exported), '--git', git, '--patch', patch],
                            env=process.sanitized_environment())
        require(identity == source_identity(git), 'pkgsrc export inputs changed during verification')
        require(archive and os.path.isabs(archive),
                'changed wpa_supplicant inputs require an explicit archive for payload comparison')
        prepared = prepare(archive, hostapd_archive, Path(tmp) / 'expected', patch, git, exported=exported)
        require(identity == source_identity(git), 'pkgsrc export inputs changed during verification')
        require(prepared['tree_sha256'] == record['tree_sha256'],
                'prepared wpa_supplicant differs from current effective source')
    return record


def prepare(archive, hostapd_archive, output, patch, git, exported=None):
    require(os.path.isabs(git) and os.path.isabs(patch), 'select absolute Git and patch executables')
    output = Path(output)
    require(output.is_absolute(), 'prepared source output must be absolute')
    output = Path(paths.canonical_existing(output.parent), output.name)
    require(not os.path.lexists(output), 'prepared source output already exists')
    paths.reject_overlap(str(output), str(PORTS))
    identity = source_identity(git)
    with tempfile.TemporaryDirectory(prefix='.wpa_supplicant-source-', dir=output.parent) as tmp:
        tmp = Path(tmp)
        if exported is None:
            exported = tmp / 'pkgsrc'
            process.capture([sys.executable, '-B', str(PORTS / 'scripts/prepare-pkgsrc.py'),
                             str(exported), '--git', git, '--patch', patch],
                            env=process.sanitized_environment())
        metadata, patches = recipe(exported)
        archives = []
        for selected, name in ((archive, metadata['archive']), (hostapd_archive, metadata['hostapd'])):
            require(selected and os.path.isabs(str(selected)), 'both WPA archives must be absolute')
            path = Path(paths.canonical_existing(selected))
            require(path.name == name, 'WPA archive filename differs from recipe')
            data = read(path)
            hashes = sourceprep.archive_hashes(data)
            require(all(hashes[key] == metadata['archives'][name][key]
                        for key in ('sha512', 'blake2s', 'size')), 'WPA archive checksum differs')
            packed = tmp / name
            packed.write_bytes(data)
            distname = name.removesuffix('.tar.gz')
            sourceprep.extract_archive(packed, tmp, distname, 'wpa_supplicant')
            archives.append((path, hashes))
        root = tmp / metadata['distname']
        os.rename(tmp / metadata['hostapd'].removesuffix('.tar.gz') / 'hostapd', root / 'hostapd')
        for index, path in enumerate(patches):
            delta = read(path)
            require(digest(delta) == metadata['recipe']['patches/' + path.name], 'wpa_supplicant patch changed')
            sourceprep.apply_patch(patch, path, delta, root, 'wpa_supplicant',
                patch_args=('-p0', '-f', '-N', '-F0', '-V', 'none'),
                backup_directory=tmp / ('patch-backups-' + str(index)))
        require(not any(p.name.endswith(('.orig', '.rej')) for p in root.rglob('*')),
                'wpa_supplicant patch left a backup or reject')
        require(identity == source_identity(git), 'pkgsrc export inputs changed during preparation')
        identity = {'effective': git_effective_identity(git),
                    'owner_sha256': identity['owner_sha256']}
        record = prepared_receipt.write(root, package=PACKAGE, identity=identity)
        for path, hashes in archives:
            require(sourceprep.archive_hashes(read(path)) == hashes, 'WPA archive changed during preparation')
        publish_directory_noreplace(root, output)
    return record


def shared_tree(selected):
    """Return the run's shared pkgsrc export, bound to current inputs, if any."""
    if not selected.pkgsrc_export:
        return None
    require(selected.patch and os.path.isabs(selected.patch), 'select an absolute patch executable')
    return identity_module().shared_export(selected.pkgsrc_export, PORTS, selected.git, SDK_SOURCE, getattr(selected, 'export_patch', None) or selected.patch)


def main():
    sdk_source.install_signal_handlers()
    args = load_sdk(sys.argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git', required=True, help='absolute Git inspector')
    sub = parser.add_subparsers(dest='action', required=True)
    produce = sub.add_parser('prepare')
    produce.add_argument('--archive', required=True)
    produce.add_argument('--hostapd-archive', required=True)
    produce.add_argument('--output', required=True)
    produce.add_argument('--patch', required=True)
    produce.add_argument('--pkgsrc-export', help='shared export from scripts/pkgsrc-shared-export.py')
    produce.add_argument('--export-patch', help='patch used to create the shared export')
    check = sub.add_parser('verify-source')
    check.add_argument('--source', required=True)
    check.add_argument('--archive')
    check.add_argument('--hostapd-archive')
    check.add_argument('--patch')
    check.add_argument('--pkgsrc-export', help='shared export from scripts/pkgsrc-shared-export.py')
    check.add_argument('--export-patch', help='patch used to create the shared export')
    selected = parser.parse_args(args)
    try:
        if selected.action == 'prepare':
            record = prepare(selected.archive, selected.hostapd_archive, selected.output, selected.patch, selected.git,
                             exported=shared_tree(selected))
        else:
            record = verify(selected.source, selected.git, selected.archive, selected.hostapd_archive, selected.patch, pkgsrc_export=selected.pkgsrc_export, export_patch=getattr(selected, 'export_patch', None))
        sys.stdout.buffer.write(jsonio.json_bytes(record))
    except (SDKError, OSError, ValueError) as exc:
        sdk_source.exit_error(exc, 'wpa_supplicant source: ')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sdk_source.exit_error(error, 'wpa_supplicant source: ')
