#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Assemble the ORT-pinned Dawn source bundle from official archive inputs."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
from urllib.request import urlopen
import zipfile

ROOT = 'dawn-20260916.214021'


def safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(part in ('', '.', '..') for part in path.parts):
        raise ValueError('unsafe archive path: ' + name)
    return path.as_posix()


def add_file(output, name, mode, data, seen):
    name = safe_name(name)
    if name in seen:
        raise ValueError('duplicate bundle path: ' + name)
    seen.add(name)
    info = tarfile.TarInfo(ROOT + '/' + name)
    info.size = len(data)
    info.mode = 0o755 if mode & 0o111 else 0o644
    info.uid = info.gid = info.mtime = 0
    info.uname = info.gname = ''
    output.addfile(info, io.BytesIO(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('dawn-sources.json'))
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fetch', action='store_true', help='download missing official inputs')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if manifest['format'] != 1:
        raise ValueError('unsupported source manifest')
    args.inputs.mkdir(parents=True, exist_ok=True)
    for source in [manifest['dawn'], *manifest['dependencies']]:
        path = args.inputs / source['filename']
        if args.fetch and not path.is_file():
            with tempfile.NamedTemporaryFile(dir=args.inputs, delete=False) as staged:
                temp_path = Path(staged.name)
                try:
                    with urlopen(source['url'], timeout=180) as response:
                        while chunk := response.read(1024 * 1024):
                            staged.write(chunk)
                except BaseException:
                    temp_path.unlink(missing_ok=True)
                    raise
            temp_path.replace(path)
        if not path.is_file():
            raise ValueError('missing input: ' + str(path))
    dawn = args.inputs / manifest['dawn']['filename']
    with dawn.open('rb') as source:
        if hashlib.file_digest(source, 'sha256').hexdigest() != manifest['dawn']['sha256']:
            raise ValueError('Dawn archive SHA-256 mismatch')
    seen = set()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as temp:
        tmp = Path(temp.name)
    try:
        with tmp.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0, compresslevel=9) as gz, tarfile.open(fileobj=gz, mode='w|', format=tarfile.PAX_FORMAT) as out:
            with zipfile.ZipFile(dawn) as z:
                entries = sorted((x for x in z.infolist() if not x.is_dir()), key=lambda x: x.filename)
                for entry in entries:
                    prefix, slash, name = entry.filename.partition('/')
                    if not slash or not prefix.startswith('dawn-'):
                        raise ValueError('unexpected Dawn archive root')
                    mode = entry.external_attr >> 16
                    if mode & 0o170000 not in (0, 0o100000):
                        raise ValueError('unsupported Dawn archive member: ' + name)
                    add_file(out, name, mode, z.read(entry), seen)
            for source in manifest['dependencies']:
                records = []
                with tarfile.open(args.inputs / source['filename'], 'r:gz') as archive:
                    previous = ''
                    for entry in archive:
                        if entry.isdir():
                            continue
                        if not entry.isfile():
                            raise ValueError('unsupported dependency member: ' + entry.name)
                        name = safe_name(entry.name.removeprefix('./'))
                        if name <= previous:
                            raise ValueError('dependency archive is not sorted or has duplicate paths')
                        previous = name
                        data = archive.extractfile(entry).read()
                        mode = '755' if entry.mode & 0o111 else '644'
                        records.append(f'{name}\0{mode}\0{hashlib.sha256(data).hexdigest()}\n')
                        add_file(out, source['path'] + '/' + name, entry.mode, data, seen)
                tree = hashlib.sha256(''.join(records).encode()).hexdigest()
                if tree != source['tree_sha256']:
                    raise ValueError('dependency tree SHA-256 mismatch: ' + source['path'])
        tmp.replace(args.output)
    finally:
        tmp.unlink(missing_ok=True)
    with args.output.open('rb') as f:
        print('SHA256', hashlib.file_digest(f, 'sha256').hexdigest(), args.output)


if __name__ == '__main__':
    main()
