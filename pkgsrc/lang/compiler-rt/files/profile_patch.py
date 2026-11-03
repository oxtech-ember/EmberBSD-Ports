# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Shared pkgsrc profile patch identity.
"""Check the shared patch against its compiler-rt owner checksum."""
import hashlib
import re

NAME = 'patch-13-profile-gpu-bounds'


def patch_checksum(data):
    filtered = b''.join(line for line in data.splitlines(True) if b'$NetBSD' not in line)
    return hashlib.sha1(filtered).hexdigest()


def verified_patch(patch_file, distinfo):
    if patch_file.name != NAME:
        raise ValueError('wrong shared patch name')
    data = patch_file.read_bytes()
    info = distinfo.read_text(encoding='utf-8')
    values = re.findall(r'^SHA1 \(' + re.escape(NAME) + r'\) = ([0-9a-f]{40})$', info, re.M)
    if len(values) != 1 or patch_checksum(data) != values[0]:
        raise ValueError('shared patch checksum missing, duplicate or mismatched')
    return data
