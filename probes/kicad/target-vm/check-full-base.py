#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Full-base archive and staging regressions.
"""Check full-base metadata and causal archive guards without an image or VM."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile
import full_base


def require(value, message):
    if not value:
        raise ValueError(message)


def item(name, kind, mode=0o755, uid=0, gid=0, link=''):
    result = tarfile.TarInfo(name)
    result.type, result.mode, result.uid, result.gid, result.linkname = kind, mode, uid, gid, link
    if kind == tarfile.REGTYPE:
        result.size = len(b'actual fixture payload\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('new_work', type=Path)
    args = parser.parse_args()
    work = args.new_work.resolve()
    require(work == args.new_work and not work.exists() and not work.is_symlink(),
            'Use a new absolute canonical work directory.')
    work.mkdir(mode=0o700)
    failures = {}
    release_manifest = work / 'release-manifest.json'
    release_manifest.write_bytes(b'{"source_commit":"fixture"}\n')
    release_pin = hashlib.sha256(release_manifest.read_bytes()).hexdigest()
    require(full_base.verify_release_manifest(release_manifest, release_pin) == release_pin,
            'Pinned release manifest digest was not accepted.')
    release_manifest.write_bytes(b'{"source_commit":"changed"}\n')
    try:
        full_base.verify_release_manifest(release_manifest, release_pin)
    except ValueError as error:
        failures['changed-release-manifest'] = str(error)
    else:
        raise ValueError('Modified release manifest was accepted.')
    good = [item('.', tarfile.DIRTYPE), item('bin', tarfile.DIRTYPE),
            item('bin/tool', tarfile.REGTYPE, 0o6755, 0, 2),
            item('bin/alias', tarfile.LNKTYPE, 0o6755, 0, 2, 'bin/tool'),
            item('bin/unreadable', tarfile.REGTYPE, 0),
            item('bin/symbolic', tarfile.SYMTYPE, 0o777, link='/bin/tool')]
    runtime = [
        item('usr/pkg', tarfile.DIRTYPE), item('usr/pkg/llvm', tarfile.DIRTYPE),
        item('usr/pkg/llvm/lib', tarfile.DIRTYPE),
        item('usr/pkg/llvm/lib/libc++.so.1', tarfile.SYMTYPE, 0o777, link='libc++.so.1.0'),
        item('usr/pkg/llvm/lib/libc++.so.1.0', tarfile.REGTYPE),
        item('usr/pkg/llvm/lib/libc++abi.so', tarfile.SYMTYPE, 0o777, link='libc++abi.so.1'),
        item('usr/pkg/llvm/lib/libc++abi.so.1', tarfile.SYMTYPE, 0o777, link='libc++abi.so.1.0'),
        item('usr/pkg/llvm/lib/libc++abi.so.1.0', tarfile.REGTYPE),
        item('usr/pkg/llvm/lib/libunwind.so', tarfile.SYMTYPE, 0o777, link='libunwind.so.1'),
        item('usr/pkg/llvm/lib/libunwind.so.1', tarfile.SYMTYPE, 0o777, link='libunwind.so.1.0'),
        item('usr/pkg/llvm/lib/libunwind.so.1.0', tarfile.REGTYPE),
        item('usr/pkg/llvm/share', tarfile.DIRTYPE),
        item('usr/pkg/llvm/share/licenses', tarfile.DIRTYPE),
        item('usr/pkg/llvm/share/licenses/compiler-rt', tarfile.DIRTYPE),
        item('usr/pkg/llvm/share/licenses/compiler-rt/CREDITS.TXT', tarfile.REGTYPE),
        item('usr/pkg/llvm/share/licenses/compiler-rt/LICENSE.EmberBSD-BINARY128.TXT', tarfile.REGTYPE),
        item('usr/pkg/llvm/share/licenses/compiler-rt/LICENSE.EmberBSD-GCOV.TXT', tarfile.REGTYPE),
        item('usr/pkg/llvm/share/licenses/compiler-rt/LICENSE.TXT', tarfile.REGTYPE),
        item('usr/pkg/llvm/share/licenses/libcxx', tarfile.DIRTYPE),
        item('usr/pkg/llvm/share/licenses/libcxx/LICENSE.TXT', tarfile.REGTYPE),
        item('usr/pkg/llvm/share/licenses/libcxxabi', tarfile.DIRTYPE),
        item('usr/pkg/llvm/share/licenses/libcxxabi/LICENSE.TXT', tarfile.REGTYPE),
        item('usr/pkg/llvm/share/licenses/libunwind', tarfile.DIRTYPE),
        item('usr/pkg/llvm/share/licenses/libunwind/LICENSE.TXT', tarfile.REGTYPE),
    ]
    runtime_inventory = {'usr/pkg': {'kind': 'directory'}}
    for entry in runtime:
        row = {'kind': 'directory' if entry.isdir() else 'link' if entry.issym() else 'file',
               'mode': entry.mode}
        if entry.issym():
            row['target'] = entry.linkname
        elif entry.isreg():
            row.update(size=entry.size, sha256=hashlib.sha256(b'actual fixture payload\n').hexdigest())
        runtime_inventory[entry.name] = row
    def archive(name, entries):
        path = work / (name + '.tar')
        with tarfile.open(path, 'w') as stream:
            for entry in entries:
                stream.addfile(entry, io.BytesIO(b'actual fixture payload\n') if entry.isreg() else None)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()
    source, digest = archive('valid', good + [item('usr', tarfile.DIRTYPE)] + runtime)
    entries = full_base.records(source, digest, runtime_inventory)
    root = work / 'root'
    root.mkdir(mode=0o700)
    payload = full_base.stage(source, entries, root)
    require((root / 'bin/tool').stat().st_ino == (root / 'bin/alias').stat().st_ino,
            'Archive hardlink identity was lost.')
    require((root / 'bin/tool').stat().st_nlink == 2, 'Hardlink count is incorrect.')
    require(stat.S_IMODE((root / 'bin/tool').stat().st_mode) & 0o6000 == 0,
            'Host staging gained target set-ID bits.')
    require((root / 'bin/unreadable').read_bytes() == b'actual fixture payload\n',
            'A target mode-000 file became unavailable to makefs.')
    require((root / 'bin/symbolic').readlink() == Path('/bin/tool'), 'Image symlink target changed.')
    require(stat.S_IMODE(root.stat().st_mode) == 0o700, 'Private host root permissions changed.')
    require(hashlib.sha256(source.read_bytes()).hexdigest() == digest, 'Archive input changed.')
    metadata = full_base.metadata(entries)
    for line in ['./bin/tool type=file uid=0 gid=2 mode=06755\n',
                 './bin/alias type=file uid=0 gid=2 mode=06755\n',
                 './bin/unreadable type=file uid=0 gid=0 mode=00\n',
                 '. type=dir uid=0 gid=0 mode=0755\n']:
        require(line in metadata, 'Target metadata was not preserved: ' + line)
    variants = {
        'duplicate': good + [copy.copy(good[2])],
        'absolute': good + [item('/outside', tarfile.REGTYPE)],
        'traversal': good + [item('../outside', tarfile.REGTYPE)],
        'symlink-parent': good + [item('bin/symbolic/child', tarfile.REGTYPE)],
        'dangling-hardlink': good + [item('bin/dangling', tarfile.LNKTYPE, link='bin/missing')],
        'hardlink-metadata': good + [item('bin/conflict', tarfile.LNKTYPE, 0o644, link='bin/tool')],
        'escaped-symlink': good + [item('bin/escape', tarfile.SYMTYPE, link='../../outside')],
        'noncanonical-root': [item('.', tarfile.DIRTYPE, 0o700)] + good[1:],
        'wrong-root-owner': [item('.', tarfile.DIRTYPE, uid=1)] + good[1:],
        'missing-root': good[1:],
        'special-file': good + [item('bin/device', tarfile.CHRTYPE)],
        'compiler': good + [item('usr', tarfile.DIRTYPE), item('usr/bin', tarfile.DIRTYPE), item('usr/bin/gcc', tarfile.REGTYPE)],
        'packages': good + [item('usr', tarfile.DIRTYPE), item('usr/pkg', tarfile.DIRTYPE), item('usr/pkg/file', tarfile.REGTYPE)],
        'runtime-compiler': good + runtime + [item('usr/pkg/llvm/bin', tarfile.DIRTYPE),
                                             item('usr/pkg/llvm/bin/clang', tarfile.REGTYPE)],
        'runtime-extra-package': good + runtime + [item('usr/pkg/extra', tarfile.DIRTYPE),
                                                   item('usr/pkg/extra/file', tarfile.REGTYPE)],
        'runtime-wrong-link': good + [item('usr', tarfile.DIRTYPE)] + [
            item(entry.name, entry.type, entry.mode, entry.uid, entry.gid,
                 'libc++.so.1.1' if entry.name == 'usr/pkg/llvm/lib/libc++.so.1' else entry.linkname)
            for entry in runtime],
    }
    for name, variant in variants.items():
        path, checksum = archive(name, variant)
        try:
            full_base.records(path, checksum, runtime_inventory)
        except ValueError as error:
            failures[name] = str(error)
        else:
            raise ValueError('Invalid archive accepted: ' + name)
    for name, checksum in [('wrong-hash', '0' * 64), ('missing-hash', None)]:
        try:
            full_base.records(source, checksum)
        except ValueError as error:
            failures[name] = str(error)
        else:
            raise ValueError('Invalid hash accepted: ' + name)
    etc_good = [item('etc', tarfile.DIRTYPE), item('etc/master.passwd', tarfile.REGTYPE, 0o600),
                item('etc/zoneinfo', tarfile.SYMTYPE, 0o777, link='/usr/share/zoneinfo/UTC'),
                item('.profile', tarfile.REGTYPE), item('root', tarfile.DIRTYPE),
                item('root/.profile', tarfile.LNKTYPE, link='.profile')]
    etc_archive, etc_digest = archive('valid-etc', etc_good)
    etc_entries = full_base.etc_records(etc_archive, etc_digest)
    etc_root = work / 'etc-root'
    (etc_root / 'etc').mkdir(parents=True)
    etc_payload = full_base.stage_etc(etc_archive, etc_entries, etc_root)
    require((etc_root / 'root/.profile').stat().st_ino == (etc_root / '.profile').stat().st_ino,
            'Release etc-set hardlink identity was lost.')
    require((etc_root / 'etc/zoneinfo').readlink() == Path('/usr/share/zoneinfo/UTC'),
            'Release etc-set symlink target changed.')
    require(etc_payload['etc/master.passwd'] == hashlib.sha256(b'actual fixture payload\n').hexdigest(),
            'Release etc-set payload hash was not recorded.')
    outside = work / 'existing-base-directory'
    outside.mkdir()
    protected = outside / 'host-file'
    protected.write_bytes(b'keep this file unchanged\n')
    linked_root = work / 'base-with-linked-etc'
    linked_root.mkdir()
    (linked_root / 'etc').symlink_to(outside, target_is_directory=True)
    attack_archive, attack_digest = archive('etc-linked-parent', [item('etc/payload', tarfile.REGTYPE)])
    attack_entries = full_base.etc_records(attack_archive, attack_digest)
    try:
        full_base.stage_etc(attack_archive, attack_entries, linked_root)
    except ValueError as error:
        failures['etc-base-symlink-parent'] = str(error)
    else:
        raise ValueError('Etc-set payload was staged through a base symlink parent.')
    require(protected.read_bytes() == b'keep this file unchanged\n' and not (outside / 'payload').exists(),
            'Rejected etc-set payload changed a file reached through a base symlink.')
    for name, variant in [('etc-duplicate', etc_good + [copy.copy(etc_good[1])]),
                          ('etc-escaped-link', etc_good + [item('etc/escape', tarfile.SYMTYPE, link='../../outside')]),
                          ('etc-special', etc_good + [item('etc/device', tarfile.CHRTYPE)])]:
        path, checksum = archive(name, variant)
        try:
            full_base.etc_records(path, checksum)
        except ValueError as error:
            failures[name] = str(error)
        else:
            raise ValueError('Invalid etc set accepted: ' + name)
    metalog = work / 'etc.mtree'
    metalog.write_text('./etc/hosts type=file uname=root gname=wheel mode=0644 size=99 sha256=old time=0\n')
    require(full_base.etc_metadata(metalog) == './etc/hosts type=file uname=root gname=wheel mode=0644\n',
            'Configuration metadata retained a stale content hash.')
    accounts = work / 'accounts'
    (accounts / 'etc').mkdir(parents=True)
    (accounts / 'etc/group').write_text('wheel:*:0:root\n')
    (accounts / 'etc/master.passwd').write_text('root:*:0:0::0:0:root:/root:/bin/sh\n')
    user = full_base.add_user(accounts)
    require('ember:*:1000:1000::0:0:EmberBSD runtime:/home/ember:/bin/sh\n' in
            (accounts / 'etc/master.passwd').read_text(), 'Runtime account is incorrect.')
    require('./home/ember type=dir uid=1000 gid=1000 mode=0700\n' in user, 'Runtime owner metadata is incorrect.')
    snapshot = {path: path.read_bytes() for path in (accounts / 'etc').iterdir()}
    try:
        full_base.add_user(accounts)
    except ValueError as error:
        failures['account-collision'] = str(error)
    else:
        raise ValueError('Duplicate runtime account accepted.')
    require(snapshot == {path: path.read_bytes() for path in snapshot}, 'Rejected account changed source accounts.')
    (work / 'artifacts').mkdir()
    receipt = work / 'artifacts/staging.json'
    staging = dict(base_profile='full', base_revision='1' * 40, base=str(source),
                   archive_sha256=digest, full_base=dict(payload_sha256=payload,
                                                        runtime_inventory=runtime_inventory))
    receipt.write_text(json.dumps(staging))
    manifest = {name: staging[name] for name in ('base', 'base_revision', 'base_profile')}
    manifest['staging_sha256'] = hashlib.sha256(receipt.read_bytes()).hexdigest()
    inputs = full_base.runtime_inputs(manifest, work)
    require(inputs['base'] == str(root), 'Full-base query input is not private staging.')
    require(inputs['sources_sha256'][str(root / 'bin/alias')] == payload['bin/tool'],
            'Runtime hardlink lost its original archive hash.')
    require(inputs['sources_sha256'][str(root / 'bin/symbolic')] == {'symlink': '/bin/tool'},
            'Runtime symlink lost its original archive target.')
    for label, overrides in [('receipt-hash', {'staging_sha256': '0' * 64}),
                             ('receipt-identity', {'base_revision': '2' * 40})]:
        try:
            full_base.runtime_inputs(dict(manifest, **overrides), work)
        except ValueError as error:
            failures[label] = str(error)
        else:
            raise ValueError('Invalid runtime staging receipt accepted: ' + label)
    (work / 'results.json').write_text(json.dumps(dict(
        status='pass', negative_controls=failures, payload_sha256=payload,
        etc_set_payload_sha256=etc_payload,
        helper_sha256=hashlib.sha256(Path(full_base.__file__).read_bytes()).hexdigest(),
        scope='Real tar archive parsing, hardlink staging, target metadata and account guards. No FFS image or guest execution.'), indent=2) + '\n')
    print(f'PASS: archive metadata, hardlinks, ordinary user and {len(failures)} causal guards; no image or VM.')


if __name__ == '__main__':
    main()
