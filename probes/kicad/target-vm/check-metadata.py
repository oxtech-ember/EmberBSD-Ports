#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual finite FFS2 root/fstat metadata regressions.
import hashlib
import os
from pathlib import Path
import re
import shutil
import struct
from vm import FSTAT_METADATA, OWNER, canonical, entrypoint, parser, root_metadata, sdk, write


def main():
    args = parser(__doc__, ['base', 'os_repository', 'revision', 'netbsd_tools', 'new_work']).parse_args()
    inventory, jsonio, paths, process, identity = sdk(args.sdk_source)
    from emberbsd_sdk.errors import CommandError
    base, source, tools = map(canonical, [args.base, args.os_repository, args.netbsd_tools])
    revision = str(args.revision)
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Use a full source commit.')
    work = Path(paths.canonical_new(args.new_work))
    if not args.new_work.is_absolute() or work.exists() or work.is_symlink():
        raise ValueError('Use a new absolute output directory.')
    def snapshot(path):
        s = path.stat()
        return dict(sha256=inventory.sha256_file(path), mode=s.st_mode, uid=s.st_uid, gid=s.st_gid,
                    device=s.st_dev, inode=s.st_ino, bytes=s.st_size, mtime_ns=s.st_mtime_ns)
    original = {name: snapshot(base / 'usr/bin' / name) for name in ['tee', 'fstat']}
    for name in original:
        with (base / 'usr/bin' / name).open('rb') as stream:
            header = stream.read(20)
        if header[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', header, 18)[0] != 183:
            raise ValueError('Use genuine AArch64 base executables.')
    work.mkdir(mode=0o700)
    (work / 'source/etc/mtree').mkdir(mode=0o700, parents=True)
    commands = []
    def run(label, *argv):
        argv = list(map(str, argv))
        try:
            result = process.capture(argv)
            out, err, code = result.stdout, result.stderr, 0
        except CommandError as error:
            out, err, code = error.stdout, error.stderr, error.returncode
        write(work / (label + '.stdout'), out)
        write(work / (label + '.stderr'), err)
        commands.append(dict(name=label, argv=argv, status=code))
        jsonio.write_json(str(work / 'commands.json'), commands, exclusive=False)
        if code:
            raise ValueError(f'Command failed: {label}')
        return out
    pins = {}
    for relative in ['etc/group', 'etc/master.passwd', 'etc/mtree/NetBSD.dist.base', 'sys/ufs/ufs/dinode.h']:
        content = run('source-' + relative.replace('/', '-'), 'git', '-C', source, 'show', revision + ':' + relative)
        output = work / 'source' / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        write(output, content)
        pins[relative] = hashlib.sha256(content).hexdigest()
    etc = work / 'source/etc'
    group = [line.split(':')[:3] for line in (etc / 'group').read_text().splitlines()]
    if group.count(['kmem', '*', '2']) != 1:
        raise ValueError('Use the canonical kmem group.')
    canonical_root = root_metadata(etc, tools, run)
    images = {}
    for case in ['root', 'fstat']:
        staging = work / case
        staging.mkdir(mode=0o700)
        if case == 'root':
            src, dst = base / 'usr/bin/tee', staging / 'tee'
            override = canonical_root
        else:
            src, dst = base / 'usr/bin/fstat', staging / 'usr/bin/fstat'
            dst.parent.mkdir(parents=True)
            override = FSTAT_METADATA
        os.link(src, dst)
        generated = '/set uid=0 gid=0\n' + run(case + '-mtree', tools / 'nbmtree', '-c', '-k', 'type,mode,link', '-p', staging).decode()
        cases = [('before', generated, 0o700 if case == 'root' else original['fstat']['mode'] & 0o7777, 0),
                 ('fixed', generated + override, 0o755 if case == 'root' else 0o2555, 0 if case == 'root' else 2)]
        images[case] = {}
        for label, spec, mode, gid in cases:
            stem = case + '-' + label
            definition, image = work / (stem + '.mtree'), work / (stem + '.ffs')
            write(definition, spec)
            flat = run(stem + '-flat', tools / 'nbmtree', '-C', '-N', etc, '-f', definition).decode()
            name = '.' if case == 'root' else './usr/bin/fstat'
            records = [line.split()[1:] for line in flat.splitlines() if line.split()[:1] == [name]]
            expected = sorted(['type=dir' if case == 'root' else 'type=file', 'uid=0', f'gid={gid}', f'mode=0{mode:o}'])
            if len(records) != 1 or sorted(records[0]) != expected:
                raise ValueError(f'Wrong resolved {case} metadata.')
            run(stem + '-makefs', tools / 'nbmakefs', '-t', 'ffs', '-B', 'little', '-Z', '-s', '2m', '-o', 'version=2',
                '-F', definition, '-N', etc, image, staging)
            # Pinned ufs2_dinode fields: mode/nlink/uid/gid at 0/2/4/8,
            # size at 16, inode size 256. Only one matching object in the fixture.
            prefix = struct.pack('<HHII', (0o40000 if case == 'root' else 0o100000) | mode, 2 if case == 'root' else 1, 0, gid)
            if prefix in src.read_bytes():
                raise ValueError('Ambiguous fixture payload.')
            data = image.read_bytes()
            matches = [offset for offset in range(0, len(data) - 256, 256) if data.startswith(prefix, offset) and
                       struct.unpack_from('<Q', data, offset + 16)[0] == (512 if case == 'root' else original['fstat']['bytes'])]
            if len(matches) != 1:
                raise ValueError(f'Written FFS2 {case} metadata does not match.')
            images[case][label] = dict(uid=0, gid=gid, mode=f'0{mode:o}', inode_offset=matches[0],
                sha256=inventory.sha256_file(image), allocated_bytes=image.stat().st_blocks * 512)
        before, fixed = images[case]['before'], images[case]['fixed']
        if before['inode_offset'] != fixed['inode_offset']:
            raise ValueError('Inode placement changed.')
        if case == 'root':
            offset = before['inode_offset']
            if (work / 'root-before.ffs').read_bytes()[offset + 2:offset + 256] != (work / 'root-fixed.ffs').read_bytes()[offset + 2:offset + 256]:
                raise ValueError('Other root inode fields changed.')
        if (staging.stat().st_mode & 0o7777) != 0o700:
            raise ValueError('Host staging permissions changed.')
    canonical_text = (etc / 'mtree/NetBSD.dist.base').read_text()
    controls = {'private-root': canonical_text.replace('mode=0755', 'mode=0700', 1),
                'wrong-owner': canonical_text.replace('uname=root', 'uid=1', 1),
                'missing-root': ''.join(line for line in canonical_text.splitlines(keepends=True) if line.split()[:1] != ['.']),
                'duplicate-root': canonical_text + '\n.\n'}
    negative_results = {}
    for name, text in controls.items():
        variant = work / name
        (variant / 'mtree').mkdir(parents=True)
        for filename in ['group', 'master.passwd']:
            shutil.copyfile(etc / filename, variant / filename)
        write(variant / 'mtree/NetBSD.dist.base', text)
        try:
            root_metadata(variant, tools, lambda label, *argv: run(name + '-' + label, *argv))
        except ValueError as error:
            negative_results[name] = str(error)
        else:
            raise ValueError('Invalid canonical root accepted: ' + name)
    if original != {name: snapshot(base / 'usr/bin' / name) for name in original}:
        raise ValueError('Hardlinked base input changed.')
    jsonio.write_json(str(work / 'result.json'), dict(result='PASS', source_revision=revision, source=original,
        pinned_source_sha256=pins, images=images, other_root_inode_fields_unchanged=True, negative_controls=negative_results,
        tool_sha256={name: inventory.sha256_file(tools / name) for name in ['nbmtree', 'nbmakefs']},
        helper_sha256={name: inventory.sha256_file(OWNER / name) for name in ['build.py', 'vm.py', 'check-metadata.py']},
        scope='Actual shared builder helpers and four small FFS2 images; private staging and immutable base unchanged. No guest execution.'))
    print('PASS: actual FFS2 canonical root and root:kmem/02555, four source guards, unchanged base and staging.')


if __name__ == '__main__':
    entrypoint(main)
