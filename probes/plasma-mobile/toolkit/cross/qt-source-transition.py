#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Apply the selected Qt module owner patches without discarding build objects."""
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
    old_rows = marker.read_text().splitlines() if marker.exists() else []
    old_sources = {}
    if old_rows:
        if len(old_rows) != 2 * len(entries):
            raise ValueError('Qt module patch target set changed')
        for row, (_, name) in zip(old_rows[len(entries):], entries):
            expected, sep, recorded_name = row.partition('  ')
            if not sep or recorded_name != name or len(expected) != 64:
                raise ValueError('Qt module patch target set changed')
            old_sources[name] = expected
    pending = []
    with tarfile.open(archive, 'r:xz') as tar, tempfile.TemporaryDirectory(prefix='qt-module-patch-') as temp:
        scratch = Path(temp)
        for patch, name in entries:
            current = source / name
            if current.is_symlink() or not current.is_file() or not current.resolve().is_relative_to(source.resolve()):
                raise ValueError('missing or symlinked Qt module patch target: ' + name)
            member = tar.getmember(source.name + '/' + name)
            if not member.isfile():
                raise ValueError('Qt module archive target is not a regular file: ' + name)
            original = tar.extractfile(member).read()
            staged = scratch / name
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(original)
            subprocess.run([patch_command, '-d', str(scratch), '-p0', '-F0', '-i', str(patch.resolve())], check=True)
            updated = staged.read_bytes()
            content = current.read_bytes()
            if content == updated:
                continue
            if content == original and not old_rows:
                pending.append((current, updated))
            elif old_rows and digest(content) == old_sources[name]:
                pending.append((current, updated))
            else:
                raise ValueError('Qt module source differs from upstream and selected patch: ' + name)
    if plan:
        return
    # Keep every previous marker before writing any source, so interruption at
    # any point can be retried against either the old hash or the new output.
    if old_rows and old_rows != patch_rows + [f'{digest((source / name).read_bytes())}  {name}' for _, name in entries]:
        previous = marker.with_name(marker.name + '.previous-' + digest(marker.read_bytes()))
        if not previous.exists():
            previous.write_bytes(marker.read_bytes())
    for current, updated in pending:
        with tempfile.NamedTemporaryFile(dir=current.parent, prefix='.qt-transition-', delete=False) as output:
            temporary = Path(output.name)
            try:
                output.write(updated)
                output.flush()
                temporary.chmod(current.stat().st_mode)
                temporary.replace(current)
            finally:
                temporary.unlink(missing_ok=True)
    rows = patch_rows + [f'{digest((source / name).read_bytes())}  {name}' for _, name in entries]
    temporary = marker.with_name(marker.name + '.tmp')
    temporary.write_text('\n'.join(rows) + '\n')
    temporary.replace(marker)


if __name__ == '__main__':
    try:
        if len(sys.argv) < 7 or sys.argv[1] not in ('apply', 'plan'):
            raise ValueError('usage: qt-source-transition.py apply|plan SOURCE ARCHIVE MARKER PATCH PATCHES...')
        transition(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6:], sys.argv[1] == 'plan')
    except (OSError, ValueError, KeyError, tarfile.TarError, subprocess.CalledProcessError) as error:
        print('Qt module source transition: ' + str(error), file=sys.stderr)
        sys.exit(1)
