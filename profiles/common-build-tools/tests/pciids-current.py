#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted source and package-export regression.
"""Check the pinned PCI ID snapshot and pkgsrc replacement export."""

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', required=True)
parser.add_argument('--ports-root', required=True)
parser.add_argument('--upstream-pkgsrc', required=True)
parser.add_argument('--archive', required=True)
parser.add_argument('--work', required=True)
args = parser.parse_args()
if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 15):
    parser.error('CPython 3.15 is required.')
sdk = Path(args.sdk_source).resolve(strict=True)
sys.path.insert(0, str(sdk / 'src'))
import emberbsd_sdk
from emberbsd_sdk import errors, inventory, jsonio, paths, process
from emberbsd_sdk.errors import CommandError, SDKError

sdk_package = (sdk / 'src/emberbsd_sdk').resolve(strict=True)
if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error('EmberBSD SDK host API 1 is required.')
for module in (emberbsd_sdk, errors, inventory, jsonio, paths, process):
    module_path = Path(module.__file__).resolve(strict=True)
    if not module_path.is_relative_to(sdk_package):
        parser.error(f'SDK module is outside the selected SDK source: {module.__name__}')

COMMIT = '86e7077e4b7947be28d4de891c69f7ae64da0286'
ARCHIVE = f'pci.ids-{COMMIT}.tar.gz'
ARCHIVE_SHA256 = '0935bb070fcb0a199e0a918e977e233e57a463f0e518733f3377bee8ab120f72'
ARCHIVE_SIZE = 380456
VERSION = '2026.10.22'
PKGNAME = 'pciids-20261022'
EXPECTED = {
    ('1002', '7550'): 'Navi 48 [Radeon RX 9070/9070 XT/9070 GRE]',
    ('10de', '2b85'): 'GB202 [GeForce RTX 5090]',
    ('14c3', '7925'): 'MT7925 802.11be 160MHz 2x2 PCIe Wireless Network Adapter [Filogic 360]',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data, algorithm):
    return hashlib.new(algorithm, data).hexdigest()


def devices(text):
    vendor = None
    found = {}
    vendor_pattern = re.compile(r'^([0-9a-fA-F]{4})[ \t]+(.+)$')
    device_pattern = re.compile(r'^\t([0-9a-fA-F]{4})[ \t]+(.+)$')
    for line in text.splitlines():
        if not line or line.startswith('#'):
            continue
        if not line.startswith('\t'):
            match = vendor_pattern.fullmatch(line)
            vendor = match.group(1).lower() if match else None
            continue
        if line.startswith('\t\t') or vendor is None:
            continue
        match = device_pattern.fullmatch(line)
        if match:
            found[(vendor, match.group(1).lower())] = match.group(2)
    return found


def only_file(archive, relative):
    with tarfile.open(archive, 'r:gz') as source:
        members = source.getmembers()
        require(len(members) <= 8, 'Unexpectedly large source archive inventory.')
        for member in members:
            name = PurePosixPath(member.name)
            require(not name.is_absolute() and '..' not in name.parts,
                    'Unsafe archive member path.')
            require(member.isfile() or member.isdir(), 'Unexpected special archive member.')
        selected = [member for member in members if member.name == relative]
        require(len(selected) == 1 and selected[0].isfile(),
                'Pinned archive does not contain exactly one expected pci.ids file.')
        handle = source.extractfile(selected[0])
        require(handle is not None, 'Cannot read the pinned pci.ids file.')
        data = handle.read(4 * 1024 * 1024 + 1)
        require(len(data) <= 4 * 1024 * 1024, 'pci.ids exceeds the bounded source size.')
        return data


def run_export(root, destination, archive_root, path):
    env = {
        'PATH': str(path) + os.pathsep + os.defpath,
        'FAKE_ARCHIVE': str(archive_root),
        'FAKE_PIN': 'fff4deb639a1a640476203c80f752fb77b6cb14b',
        'LC_ALL': 'C',
        'GIT_OPTIONAL_LOCKS': '0',
        'GIT_NO_LAZY_FETCH': '1',
    }
    argv = [shutil.which('sh'), str(root / 'scripts/prepare-pkgsrc.sh'), str(destination)]
    try:
        result = process.capture(argv, cwd=str(root), env=env)
        return dict(status=result.returncode, stdout=result.stdout.decode('utf-8', 'replace'),
                    stderr=result.stderr.decode('utf-8', 'replace'), argv=argv)
    except CommandError as error:
        return dict(status=error.returncode,
                    stdout=error.stdout.decode('utf-8', 'replace'),
                    stderr=error.stderr.decode('utf-8', 'replace'), argv=argv)


def make_fixture(root, ports, upstream, bin_dir, replace):
    (root / 'scripts').mkdir(parents=True)
    (root / 'pkgsrc/misc').mkdir(parents=True)
    (root / 'profiles/common-build-tools/patches').mkdir(parents=True)
    (root / 'upstream/pkgsrc').mkdir(parents=True)
    shutil.copy2(ports / 'pkgsrc/defaults.mk.conf', root / 'pkgsrc/defaults.mk.conf')
    shutil.copy2(ports / 'scripts/prepare-pkgsrc.sh', root / 'scripts/prepare-pkgsrc.sh')
    shutil.copy2(ports / 'profiles/common-build-tools/patches/current-automake-tools.patch',
                 root / 'profiles/common-build-tools/patches/current-automake-tools.patch')
    shutil.copytree(ports / 'pkgsrc/misc/pciids', root / 'pkgsrc/misc/pciids')
    replacement_text = 'misc/pciids\n' if replace else ''
    (root / 'pkgsrc/replaces').write_text(replacement_text)
    git = bin_dir / 'git'
    git.write_text('''#!/bin/sh
set -eu
case "$*" in
    *ls-files*) printf '160000 fff4deb639a1a640476203c80f752fb77b6cb14b 0\\tupstream/pkgsrc\\n' ;;
    *rev-parse*) printf '%s\\n' "$FAKE_PIN" ;;
    *archive*)
        for arg do case "$arg" in --output=*) output=${arg#--output=} ;; esac; done
        tar -cf "$output" -C "$FAKE_ARCHIVE" . ;;
    *) exit 91 ;;
esac
''')
    git.chmod(0o755)


def main():
    ports = Path(paths.canonical_existing(args.ports_root))
    upstream = Path(paths.canonical_existing(args.upstream_pkgsrc))
    archive = Path(paths.canonical_existing(args.archive))
    work = Path(paths.canonical_new(args.work))
    require(not work.exists(), 'Work directory already exists.')
    for source in (ports, upstream, archive):
        paths.reject_overlap(work, source)
    require(inventory.sha256_file(archive) == ARCHIVE_SHA256,
            'The immutable upstream archive SHA256 differs.')
    require(archive.stat().st_size == ARCHIVE_SIZE,
            'The immutable upstream archive size differs.')
    source_row = (ports / 'profiles/common-build-tools/sources.tsv').read_text().splitlines()
    rows = [line.split('\t') for line in source_row
            if line and not line.startswith('#') and line.split('\t')[0] == ARCHIVE]
    require(rows == [[ARCHIVE, ARCHIVE_SHA256,
                      f'https://github.com/pciutils/pciids/archive/{COMMIT}.tar.gz']],
            'The common source pin does not match this exact upstream archive.')
    recipe = ports / 'pkgsrc/misc/pciids'
    makefile = (recipe / 'Makefile').read_text()
    require(f'PKGNAME=\tpciids-20261022' in makefile and
            f'GITHUB_TAG=\t{COMMIT}' in makefile and
            'LICENSE=\tmodified-bsd OR gnu-gpl-v2' in makefile,
            'Package version, source commit or license expression differs.')
    require(re.search(r'^USE_LANGUAGES=[ \t]*#[ \t]*none[ \t]*$', makefile, re.M) and
            re.search(r'^NO_CONFIGURE=[ \t]*yes[ \t]*$', makefile, re.M) and
            re.search(r'^NO_BUILD=[ \t]*yes[ \t]*$', makefile, re.M),
            'The data-only package must not request a compiler, configure or build phase.')
    require('misc/pciids' in (ports / 'pkgsrc/replaces').read_text().splitlines(),
            'The upstream package replacement is not declared.')
    distinfo = (recipe / 'distinfo').read_text()
    data = archive.read_bytes()
    expected_distinfo = (
        f'BLAKE2s ({ARCHIVE}) = {hashlib.blake2s(data).hexdigest()}\n'
        f'SHA512 ({ARCHIVE}) = {hashlib.sha512(data).hexdigest()}\n'
        f'Size ({ARCHIVE}) = {len(data)} bytes'
    )
    require(expected_distinfo in distinfo, 'pkgsrc distinfo hashes or size differ.')
    source_notice = (recipe / 'files/SOURCE').read_text()
    require(f'Revision: {COMMIT}' in source_notice and
            f'Archive SHA256: {ARCHIVE_SHA256}' in source_notice and
            f'Version: {VERSION}' in source_notice,
            'The package source notice does not identify this immutable input.')
    file_data = only_file(archive, f'pciids-{COMMIT}/pci.ids')
    text = file_data.decode('utf-8', 'strict')
    require(f'#\tVersion: {VERSION}' in text.splitlines()[:8],
            'The database version header differs from the pinned package version.')
    found = devices(text)
    for key, expected in EXPECTED.items():
        require(found.get(key) == expected, f'Current PCI ID mismatch for {key[0]}:{key[1]}.')
    require((recipe / 'PLIST').read_text().splitlines() ==
            ['@comment $NetBSD$', 'share/pciids/pci.ids'],
            'The package file list differs from the data-only package contract.')

    work.mkdir(mode=0o700)
    archive_root = work / 'pkgsrc-fixture'
    (archive_root / 'mk/tools').mkdir(parents=True)
    (archive_root / 'misc/pciids').mkdir(parents=True)
    for relative in ('mk/tools/automake.mk', 'misc/Makefile', 'misc/pciids/Makefile'):
        shutil.copy2(upstream / relative, archive_root / relative)
    fake_bin = work / 'fake-bin'
    fake_bin.mkdir()
    success_root = work / 'ports-export-success'
    make_fixture(success_root, ports, upstream, fake_bin, True)
    passed = run_export(success_root, work / 'exported-pkgsrc', archive_root, fake_bin)
    jsonio.write_json(work / 'export-success.json', passed)
    require(passed['status'] == 0, 'The exporter failed to replace the pinned package.')
    exported_makefile = (work / 'exported-pkgsrc/misc/pciids/Makefile').read_text()
    require(f'PKGNAME=\tpciids-20261022' in exported_makefile and
            f'GITHUB_TAG=\t{COMMIT}' in exported_makefile and
            'PKGNAME=\tpciids-20200222' not in exported_makefile,
            'The export did not contain the current package recipe.')
    require((work / 'exported-pkgsrc/misc/pciids/PLIST').is_file(),
            'The export lost the package file list.')

    fail_root = work / 'ports-export-no-replacement'
    make_fixture(fail_root, ports, upstream, fake_bin, False)
    refused = run_export(fail_root, work / 'export-without-replacement', archive_root, fake_bin)
    jsonio.write_json(work / 'export-collision.json', refused)
    require(refused['status'] != 0 and
            'add it to pkgsrc/replaces or remove it.' in refused['stderr'],
            'The exporter accepted an undeclared upstream package collision.')
    require((work / 'export-without-replacement/misc/pciids/Makefile').read_text() ==
            (upstream / 'misc/pciids/Makefile').read_text(),
            'The failed collision check modified the upstream package.')

    commands = [
        dict(label='export-declared-replacement', **passed),
        dict(label='export-undeclared-replacement', **refused),
    ]
    jsonio.write_json(work / 'result.json', dict(
        status='PASS', sdk_api=1, sdk_module_origin=str(sdk_package),
        python=sys.version.split()[0], archive=ARCHIVE,
        archive_sha256=ARCHIVE_SHA256, pci_ids_sha256=digest(file_data, 'sha256'),
        pci_ids_version=VERSION, pci_ids_lines=len(text.splitlines()),
        current_id_checks=len(EXPECTED), package=PKGNAME,
        exporter='scripts/prepare-pkgsrc.sh, synthetic pinned pkgsrc archive',
        tests=dict(source_pin=True, pkgsrc_hashes=True, license=True,
                   source_notice=True, version_header=True,
                   known_current_ids=sorted(f'{vendor}:{device}' for vendor, device in EXPECTED),
                   declared_replacement=True, undeclared_collision_refused=True),
        commands=commands,
        scope='Data-only source and pkgsrc export regression. No C compiler, package build, staging, installation or runtime test.'
    ))
    print(f'PASS: {len(EXPECTED)} current-ID checks, both exporter controls and package metadata; no compiler invoked; evidence: {work}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, SDKError, tarfile.TarError) as error:
        raise SystemExit(str(error))
