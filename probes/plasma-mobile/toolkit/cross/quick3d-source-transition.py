#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Apply the selected Quick3D owner patches without discarding build objects."""
import hashlib
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def target(patch):
    lines = Path(patch).read_text().splitlines()
    names = [line[4:].split('\t', 1)[0] for line in lines if line.startswith('+++ ')]
    if len(names) != 1:
        raise ValueError('each owner patch must change exactly one file')
    name = PurePosixPath(names[0])
    if name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0] != 'src':
        raise ValueError('unsafe owner patch target')
    return str(name)


def transition(source, archive, marker, patch_command, patches, plan=False):
    source, marker = Path(source), Path(marker)
    entries = [(Path(p), target(p)) for p in patches]
    if not entries or len({name for _, name in entries}) != len(entries):
        raise ValueError('empty or duplicate owner patch target')
    patch_rows = [f'{digest(p.read_bytes())}  {p.resolve()}' for p, _ in entries]
    if marker.exists():
        expected = marker.read_text().splitlines()
        rows = patch_rows + [f'{digest((source / name).read_bytes())}  {name}' for _, name in entries]
        if rows != expected:
            raise ValueError('Quick3D patch set or patched source changed')
        return
    pending = []
    with tarfile.open(archive, 'r:xz') as tar, tempfile.TemporaryDirectory(prefix='qt-quick3d-patch-') as temp:
        scratch = Path(temp)
        for patch, name in entries:
            current = source / name
            if current.is_symlink() or not current.is_file() or not current.resolve().is_relative_to(source.resolve()):
                raise ValueError('missing or symlinked Quick3D patch target: ' + name)
            member = tar.getmember(source.name + '/' + name)
            if not member.isfile():
                raise ValueError('Quick3D archive target is not a regular file: ' + name)
            original = tar.extractfile(member).read()
            staged = scratch / name
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(original)
            subprocess.run([patch_command, '-d', str(scratch), '-p0', '-F0', '-i', str(patch.resolve())], check=True)
            updated = staged.read_bytes()
            content = current.read_bytes()
            if content == original:
                pending.append((patch, name))
            elif content != updated:
                raise ValueError('Quick3D source differs from upstream and selected patch: ' + name)
    # Check every remaining hunk before changing any source file. A prior
    # interruption may have left some files already equal to the patched bytes.
    for patch, _ in pending:
        subprocess.run([patch_command, '-d', str(source), '-p0', '-F0', '--dry-run', '-i', str(patch.resolve())], check=True)
    if plan:
        return
    for patch, _ in pending:
        subprocess.run([patch_command, '-d', str(source), '-p0', '-F0', '-i', str(patch.resolve())], check=True)
    rows = patch_rows + [f'{digest((source / name).read_bytes())}  {name}' for _, name in entries]
    temporary = marker.with_name(marker.name + ".tmp")
    temporary.write_text('\n'.join(rows) + '\n')
    temporary.replace(marker)


if __name__ == '__main__':
    try:
        if len(sys.argv) < 7 or sys.argv[1] not in ('apply', 'plan'):
            raise ValueError('usage: quick3d-source-transition.py apply|plan SOURCE ARCHIVE MARKER PATCH PATCHES...')
        transition(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6:], sys.argv[1] == 'plan')
    except (OSError, ValueError, KeyError, tarfile.TarError, subprocess.CalledProcessError) as error:
        print('Qt Quick3D source transition: ' + str(error), file=sys.stderr)
        sys.exit(1)
