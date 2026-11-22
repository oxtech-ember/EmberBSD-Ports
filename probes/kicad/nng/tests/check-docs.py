#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the NNG reference from a pkgsrc package archive."""
import argparse
import gzip
from pathlib import PurePosixPath
import posixpath
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package")
    parser.add_argument("--without-docs", action="store_true")
    args = parser.parse_args()
    with tarfile.open(args.package) as archive:
        members = {m.name: m for m in archive}
        manual = {k: v for k, v in members.items()
                  if any(p in ("man1", "man3", "man5", "man7") for p in PurePosixPath(k).parts)}
        html = {k for k, v in members.items() if k.startswith("share/doc/nng/") and v.isfile()}
        if args.without_docs:
            assert not manual and not html
            return
        assert {"share/doc/nng/index.html", "share/doc/nng/api/init.html",
                "share/doc/nng/tools/nngcat.html"} <= html
        for key, entry in manual.items():
            if entry.issym():
                target = posixpath.normpath(posixpath.join(posixpath.dirname(key), entry.linkname))
                assert target in manual and manual[target].isfile(), (key, target)
        for name in ("nng_init.3", "libnng.3", "nngcat.1", "nng_ipc.7"):
            key = next(p for p in manual if PurePosixPath(p).name in (name, name + ".gz"))
            content = archive.extractfile(key).read()
            if key.endswith(".gz"):
                content = gzip.decompress(content)
            assert b".TH " in content, key
        print(f"Checked {len(manual)} manual entries and {len(html)} offline reference files")


if __name__ == "__main__":
    main()
