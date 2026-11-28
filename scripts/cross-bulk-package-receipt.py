#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Record a completed target archive before the build installs it."""

import hashlib
import json
import os
from pathlib import Path
import stat
import sys


def identity(path):
    value = path.stat()
    if not stat.S_ISREG(value.st_mode):
        raise ValueError(f"not a package archive: {path}")
    return [value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns]


def write(path, text):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def record(worker, root, name, archive):
    cache = Path(str(worker) + ".archive")
    current = identity(archive)
    saved = json.loads(cache.read_bytes()) if cache.exists() else None
    if saved and current == saved["identity"]:
        return saved["sha256"]
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if identity(archive) != current:
        raise ValueError(f"archive changed during verification: {archive}")
    if saved and digest != saved["sha256"]:
        raise ValueError(f"archive changed after its completion receipt: {archive}")
    write(cache, json.dumps({"identity": current, "sha256": digest}))
    if not saved:
        write(Path(str(worker) + ".packaged.result"), f"packaged {root} {name} {digest}\n")
    return digest


if __name__ == "__main__":
    try:
        worker, root, name, archive = sys.argv[1:]
        print(record(Path(worker), root, name, Path(archive)))
    except (OSError, ValueError) as error:
        sys.exit(f"cross-bulk archive receipt: {error}")
