#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the Hunspell catalog PLIST against the official release source."""

import argparse
import hashlib
from pathlib import Path
import re
import tarfile


SOURCE_SHA256 = "2e559f0c2a592ba48e421477f58e9bf7e01062277a4a7821afb52fc9401010ae"
LINGUAS = "hunspell-1.7.5/po/LINGUAS"


def check(source, plist):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Hunspell 1.7.5 source hash differs")
    with tarfile.open(source, "r:gz") as archive:
        members = [member for member in archive if member.name == LINGUAS]
        if len(members) != 1 or not members[0].isfile():
            raise ValueError("Expected one regular po/LINGUAS member")
        with archive.extractfile(members[0]) as stream:
            text = stream.read().decode("ascii")
    languages = [word for line in text.splitlines()
                 for word in line.split("#", 1)[0].split()]
    if (not languages or len(languages) != len(set(languages))
            or any(not re.fullmatch(r"[A-Za-z0-9_]+", word)
                   for word in languages)):
        raise ValueError("Invalid upstream language list")
    expected = {f"share/locale/{word}/LC_MESSAGES/hunspell.mo"
                for word in languages}
    actual = [line for line in plist.read_text(encoding="utf-8").splitlines()
              if line.startswith("share/locale/")]
    if len(actual) != len(set(actual)):
        raise ValueError("Duplicate catalog PLIST entries")
    missing = sorted(expected - set(actual))
    extra = sorted(set(actual) - expected)
    if missing or extra:
        raise ValueError(f"Catalog PLIST differs: missing={missing}, extra={extra}")
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="Official hunspell-1.7.5.tar.gz release archive")
    parser.add_argument("--plist", type=Path, required=True,
                        help="Exported textproc/hunspell/PLIST")
    args = parser.parse_args()
    try:
        count = check(args.source, args.plist)
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print(f"PASS: all {count} upstream catalogs have unique PLIST entries")


if __name__ == "__main__":
    main()
