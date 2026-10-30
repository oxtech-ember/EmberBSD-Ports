# SPDX-License-Identifier: MIT
"""Read selected Mesa sources with the recipe's archive and patch checksums."""
import hashlib
from pathlib import Path
import re
import tarfile

RECIPE = Path(__file__).resolve().parents[3] / 'pkgsrc/graphics/MesaLib'


def selected(archive):
    archive = Path(archive).resolve(strict=True)
    match = re.search(r'^DISTNAME=\s*(mesa-[0-9]+\.[0-9]+\.[0-9]+)$',
                      (RECIPE / 'Makefile').read_text(), re.M)
    if not match or archive.name != match[1] + '.tar.xz':
        raise ValueError('Archive differs from selected Mesa recipe')
    info = (RECIPE / 'distinfo').read_text()
    sha = re.search(r'^SHA512 \(' + re.escape(archive.name) + r'\) = ([0-9a-f]{128})$', info, re.M)
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha512').hexdigest()
    if not sha or sha[1] != digest:
        raise ValueError('Archive hash mismatch')
    return archive, match[1], info, digest


def patch(info, name):
    path = RECIPE / 'patches' / name
    sha = re.search(r'^SHA1 \(' + re.escape(name) + r'\) = ([0-9a-f]{40})$', info, re.M)
    data = b''.join(line for line in path.read_bytes().splitlines(keepends=True) if b'$NetBSD' not in line)
    if not sha or hashlib.sha1(data).hexdigest() != sha[1]:
        raise ValueError('Patch hash mismatch: ' + name)
    return path


def extract(archive, distname, name):
    with tarfile.open(archive, 'r:xz') as bundle:
        member = bundle.getmember(distname + '/' + name)
        if not member.isfile():
            raise ValueError('Expected a regular source file: ' + name)
        with bundle.extractfile(member) as stream:
            return stream.read()
