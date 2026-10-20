#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Python migration of the native Ruby fixtures.
"""Use actual pkgtools and tar; do not execute target programs or package scripts."""
import sys
sys.dont_write_bytecode = True
import hashlib
import os
from pathlib import Path
import shutil
import time

TESTS = Path(__file__).resolve().parents[3] / 'probes/plasma-mobile/toolkit/tests'
sys.path.insert(0, str(TESTS))
from package_set_fixture import Fixture, check, elf, metadata


def main(argv):
    f = Fixture(argv, publication=True)
    from emberbsd_sdk.errors import CommandError
    from emberbsd_sdk.jsonio import read_json
    from emberbsd_sdk.stream import run_streamed
    from emberbsd_sdk.tarstream import TAR_HEADER_FACTS_API, tar_records
    from emberbsd_sdk import publication
    check(TAR_HEADER_FACTS_API == publication.DIRECTORY_PUBLICATION_API == 1,
          'SDK raw-header facts/publication API1 required')
    publication.require_directory_publication()
    bundler = f.ports / 'profiles/installer-desktop/bundle-plasma.py'

    def command(source, destination):
        return [sys.executable, '-B', '-I', '-S', bundler, '--sdk-source', f.sdk, source, destination]

    def fixture(name, *, missing=None, not_executable=None, foreign=None, symlink=False):
        area = f.work / name
        payload, cache, database = (area / n for n in ('payload', 'cache', 'pkgdb'))
        (payload / 'bin').mkdir(parents=True); cache.mkdir(); database.mkdir()
        packages = {'plasma-fixture-leaf-1.0': ('Xwayland', 'dbus-run-session'),
                    'plasma-fixture-root-1.0': ('startplasma-wayland', 'kwin_wayland', 'plasmashell')}
        archives = []
        for package, programs in packages.items():
            files = []
            for program in programs:
                if program == missing:
                    continue
                path = payload / 'bin' / program
                path.write_bytes(elf(183 if program == foreign else 62))
                path.chmod(0o644 if program == not_executable else 0o755)
                files.append('bin/' + program)
            if symlink and 'startplasma-wayland' in programs:
                (payload / 'bin/startplasma-wayland').rename(payload / 'bin/plasma-launcher')
                (payload / 'bin/startplasma-wayland').symlink_to('/usr/bin/false' if symlink == 'escape' else 'plasma-launcher')
                if symlink == 'cycle':
                    (payload / 'bin/plasma-launcher').unlink()
                    (payload / 'bin/plasma-launcher').symlink_to('startplasma-wayland')
                files.append('bin/plasma-launcher')
            archive = f.package(cache / package, package, payload, files, arch='x86_64',
                                dependencies='plasma-fixture-leaf>=1.0' if '-root-' in package else None)
            f.database(archive, database)
            archives.append(archive)
        source = area / 'source-set'
        index = area / 'archives.txt'; index.write_text(''.join(str(a) + '\n' for a in archives))
        if foreign:
            (source / 'packages').mkdir(parents=True)
            for archive in archives:
                shutil.copy2(archive, source / 'packages' / archive.name)
            (source / 'install-order.txt').write_text(''.join(pkg + '.tgz\n' for pkg in packages))
            (source / 'roots.txt').write_text('plasma-fixture-root-1.0\n')
            (source / 'target.txt').write_bytes(metadata('x86_64'))
            (source / 'packages.sha256').write_text(''.join(
                hashlib.sha256(a.read_bytes()).hexdigest() + '  packages/' + a.name + '\n' for a in archives))
        else:
            f.run([sys.executable, '-B', '-I', '-S', f.auditor, '--sdk-source', f.sdk,
                   '--target', 'amd64', database, index, source, 'plasma-fixture-root-1.0'])
        return source

    def verify(name, source, expected=None, destination=None):
        destination = destination or f.work / ('bundle-' + name)
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
        result = f.status(command(source, destination))
        text = result.stdout + result.stderr
        (f.work / (name + '.log')).write_bytes(text)
        if expected:
            check(result.returncode != 0 and expected.encode() in text, f'{name}: did not reject {expected}: {text!r}')
            check(not destination.exists() or name in ('existing-output', 'symlink-output'), 'Failed bundle published output')
        else:
            check(result.returncode == 0, f'{name}: {text!r}')
            archive = destination / 'desktop-plasma.tar.xz'
            check(f.run([f.tar, '-xOf', archive, 'PROFILE']) == b'plasma\n', 'Wrong Plasma marker')
            check(f.run([f.tar, '-xOf', archive, 'ROOTS']) == (source / 'roots.txt').read_bytes(), 'Wrong root package names')
            hashes = f.run([f.tar, '-xOf', archive, 'SHA512'])
            for path in (source / 'packages').glob('*.tgz'):
                check(f.run([f.tar, '-xOf', archive, 'All/' + path.name]) == path.read_bytes(), 'Bundle changed archive bytes')
                check(f'SHA512 ({path.name}) = {hashlib.sha512(path.read_bytes()).hexdigest()}\n'.encode() in hashes, 'Wrong inner digest')
            provenance = read_json(destination / 'PROVENANCE.json')
            check(provenance['bundle']['bytes'] == archive.stat().st_size, 'Wrong archive size receipt')
            check(provenance['installer_capacity'] == dict(limit_bytes=512 * 1024 * 1024, fits_current_limit=True), 'Wrong installer capacity boundary')
            check(provenance['source_sha256']['target.txt'] == hashlib.sha256((source / 'target.txt').read_bytes()).hexdigest(), 'Missing source byte provenance')
            check((destination / 'SHA512').read_text() == 'SHA512 (desktop-plasma.tar.xz) = ' + hashlib.sha512(archive.read_bytes()).hexdigest() + '\n', 'Wrong outer checksum')
            def inspect(reader):
                for record in tar_records(reader):
                    if record.typeflag in (b'x', b'g'):
                        continue
                    check((record.uid, record.gid, record.uname, record.gname) == (0, 0, b'root', b'wheel'), 'Archive retained host ownership')
                    check(not any(part.startswith(b'._') or part == b'__MACOSX' for part in record.name.split(b'/')), 'Archive retained Apple metadata')
            run_streamed([f.tar, '-cf', '-', '--format=pax', '@' + str(archive)], inspect, env=f.env, timeout=300)
        check(all(hashlib.sha256(path.read_bytes()).hexdigest() == value for path, value in before.items()), 'Bundler changed source input')
        retained = list(destination.parent.glob('.' + destination.name + '-*'))
        if name == 'foreign-elf':
            check(len(retained) == 1 and ('Retained incomplete auditor workspace: ' + str(retained[0])).encode() in text, 'Failed auditor workspace was removed')
        else:
            check(not retained, 'Bundler left temporary staging')
        f.count += 1
        print('PASS: ' + name)

    valid = fixture('valid')
    verify('valid', valid)
    verify('symlink-program', fixture('symlink-program', symlink=True))
    verify('symlink-cycle', fixture('symlink-cycle', symlink='cycle'), 'Plasma program symlink cycle')
    verify('symlink-escape', fixture('symlink-escape', symlink='escape'), 'Missing Plasma program')
    verify('foreign-elf', fixture('foreign', foreign='Xwayland'), 'Wrong ELF machine')
    verify('missing-program', fixture('missing', missing='plasmashell'), 'Missing Plasma program')
    verify('not-executable', fixture('not-executable', not_executable='kwin_wayland'), 'Plasma program is not executable')
    for name in ('wrong-target', 'digest', 'roots'):
        source = f.work / name; shutil.copytree(valid, source)
        if name == 'wrong-target':
            path = source / 'target.txt'; path.write_bytes(path.read_bytes().replace(b'x86_64', b'aarch64'))
            error = 'Target receipt mismatch'
        elif name == 'digest':
            path = next((source / 'packages').glob('*.tgz'))
            with path.open('ab') as stream: stream.write(b'corrupt')
            error = 'SHA256 mismatch'
        else:
            (source / 'roots.txt').write_text('missing-root-1.0\n')
            error = 'Invalid, missing or duplicate root'
        verify(name, source, error)
    orphan_source = f.work / 'outside-closure'; shutil.copytree(valid, orphan_source)
    orphan_payload = f.work / 'orphan-payload'; orphan_payload.mkdir()
    (orphan_payload / 'orphan').write_bytes(b'orphan data\n')
    orphan = f.package(f.work / 'orphan-package', 'orphan-1.0', orphan_payload, ['orphan'], arch='x86_64')
    shutil.copy2(orphan, orphan_source / 'packages' / orphan.name)
    with (orphan_source / 'install-order.txt').open('a') as stream: stream.write(orphan.name + '\n')
    with (orphan_source / 'packages.sha256').open('a') as stream:
        stream.write(hashlib.sha256(orphan.read_bytes()).hexdigest() + '  packages/' + orphan.name + '\n')
    verify('outside-closure', orphan_source, 'Package set contains archives outside its root dependency closure')
    existing = f.work / 'existing'; existing.mkdir(); (existing / 'sentinel').write_text('preserve')
    verify('existing-output', valid, 'Output already exists', existing)
    check((existing / 'sentinel').read_text() == 'preserve', 'Existing output changed')
    link = f.work / 'output-link'; link.symlink_to(f.work / 'missing-output')
    verify('symlink-output', valid, 'Output already exists', link)
    check(os.readlink(link) == str(f.work / 'missing-output'), 'Output symlink changed')
    verify('nested-output', valid, 'Output must be outside the source package set', valid / 'output')
    race = f.work / 'race-output'
    captured = bytearray()
    def collision(reader):
        deadline = time.monotonic() + 10
        while not list(f.work.glob('.race-output-*')):
            check(time.monotonic() < deadline, 'Timed out waiting for bundle staging')
            time.sleep(0.01)
        race.mkdir(); (race / 'sentinel').write_text('preserve-race')
        while block := reader.read(1024 * 1024):
            captured.extend(block)
            check(len(captured) <= 16 * 1024 * 1024, 'Unexpected fixture output size')
    try:
        run_streamed([os.fspath(a) for a in command(valid, race)], collision, env=f.env, timeout=300)
    except CommandError as error:
        captured.extend(error.stderr)
        check(b'Cannot publish bundle output' in captured, f'Wrong publication race failure: {captured!r}')
    else:
        raise AssertionError('Concurrent destination was accepted')
    (f.work / 'concurrent-output.log').write_bytes(captured)
    check([p.name for p in race.iterdir()] == ['sentinel'] and (race / 'sentinel').read_text() == 'preserve-race', 'Concurrent output changed')
    check(not list(f.work.glob('.race-output-*')), 'Publication race left staging')
    f.count += 1; print('PASS: concurrent-output-preserved')
    print(f'PASS: {f.count} native package and tar fixtures; no target code or install scripts executed')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from bundle_plasma_controls import run_controls
    run_controls(f, bundler, valid)


if __name__ == '__main__':
    main(sys.argv[1:])
