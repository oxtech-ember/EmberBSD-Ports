#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check real package archive identities.
"""Create real archives with named and numeric owners without host account changes."""
import argparse
import grp
import os
from pathlib import Path
import pwd
import subprocess
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkg-create', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--valgrind', type=Path)
    args = parser.parse_args()
    args.work.mkdir()
    work = args.work.resolve()
    stage = work / 'root'
    stage.mkdir()
    (stage / 'payload.txt').write_text('Package ownership fixture\n')
    (work / 'PLIST').write_text('@name numeric-owner-fixture-1.0\n@cwd /usr/pkg\npayload.txt\n')
    (work / 'COMMENT').write_text('Package identity fixture\n')
    (work / 'DESC').write_text('A local metadata fixture, not a distributed package.\n')
    user = pwd.getpwuid(os.getuid()).pw_name
    group = grp.getgrgid(os.getgid()).gr_name

    def create(name, owner, owner_group):
        archive = work / (name + '.tgz')
        command = [str(args.pkg_create), '-F', 'gzip', '-u', owner,
                                 '-g', owner_group, '-I', '/usr/pkg', '-p', str(stage),
                                 '-c', str(work / 'COMMENT'), '-d', str(work / 'DESC'),
                                 '-f', str(work / 'PLIST'), str(archive)]
        if args.valgrind:
            command = [str(args.valgrind), '--leak-check=full', '--track-origins=yes',
                       '--errors-for-leak-kinds=definite,indirect,possible',
                       '--error-exitcode=99'] + command
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        (work / (name + ".log")).write_text(result.stdout + result.stderr)
        return result, archive

    cases = [('named', user, group, os.getuid(), os.getgid(), user, group),
             ('numeric', '#0', '#0', 0, 0, '', ''),
             ('numeric-distinct', '#123', '#456', 123, 456, '', ''),
             ('numeric-32-bit-max', '#4294967294', '#4294967294', 4294967294, 4294967294, '', ''),
             ('numeric-leading-zero', '#000', '#000', 0, 0, '', ''),
             ('numeric-user', '#0', group, 0, os.getgid(), '', group),
             ('numeric-group', user, '#0', os.getuid(), 0, user, '')]
    for name, owner, owner_group, uid, gid, uname, gname in cases:
        result, archive = create(name, owner, owner_group)
        if result.returncode:
            raise RuntimeError(f'{name}: {result.stderr.strip()}')
        with tarfile.open(archive) as package:
            members = package.getmembers()
            assert any(member.name == 'payload.txt' for member in members)
            for member in members:
                assert (member.uid, member.gid, member.uname, member.gname) == (uid, gid, uname, gname), (name, member.name)
            assert package.extractfile('payload.txt').read() == b'Package ownership fixture\n'
        print(f'PASS: {name}: all archive identities and payload bytes')
    invalid = ['#', '#-1', '#+1', '#1x', '#0x1', '#4294967295', '#4294967296', '#18446744073709551615', '#' + '9' * 100]
    for index, value in enumerate(invalid):
        for axis in ('user', 'group'):
            result, _ = create(f'invalid-{axis}-{index}', value if axis == 'user' else '#0',
                               value if axis == 'group' else '#0')
            assert result.returncode == 2, (axis, value, result.returncode, result.stderr)
    print('PASS: 18 invalid numeric user/group selections refused')


if __name__ == '__main__':
    main()
