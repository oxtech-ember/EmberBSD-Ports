# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Identify recipe controls that can change an AutoGen tearoff."""
import hashlib
from pathlib import Path
import re

_METADATA = re.compile(rb'^(?:PKGREVISION|CATEGORIES|MASTER_SITES|MAINTAINER|HOMEPAGE|COMMENT|LICENSE|INFO_FILES)\s*[+?:!]?=')


def generation_recipe(directory):
    directory = Path(directory)
    result = {}
    for name in ('Makefile', 'Makefile.common', 'options.mk'):
        path = directory / name
        if not path.exists():
            continue
        data = path.read_bytes()
        if name == 'Makefile':
            lines = []
            skip = False
            for line in data.splitlines():
                if skip or _METADATA.match(line):
                    skip = line.rstrip().endswith(b'\\')
                    continue
                if line.strip() and not line.lstrip().startswith(b'#'):
                    lines.append(line)
            data = b'\n'.join(lines) + b'\n'
        result[name] = hashlib.sha256(data).hexdigest()
    if 'Makefile' not in result:
        raise ValueError('AutoGen recipe Makefile is missing')
    return result
