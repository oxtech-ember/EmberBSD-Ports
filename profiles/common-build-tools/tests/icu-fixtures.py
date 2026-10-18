#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Generate target resource data on the host.
"""Prepare ICU resource fixtures with the matching full native package."""
import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sdk-source", "native-prefix", "work"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15):
        parser.error("Python 3.15 is required")
    sdk = Path(args.sdk_source).resolve(strict=True)
    sys.path.insert(0, str(sdk / "src"))
    import emberbsd_sdk
    from emberbsd_sdk import paths, process
    if emberbsd_sdk.API_VERSION != 1:
        parser.error("SDK library API 1 is required")
    prefix = Path(paths.canonical_existing(args.native_prefix))
    work = Path(paths.canonical_new(args.work))
    for item in (sdk, prefix, Path(__file__).resolve().parents[1]):
        paths.reject_overlap(str(work), str(item))
    version = process.capture([str(prefix / "bin/icu-config"), "--version"])
    if version.stdout.decode("utf-8").strip() != "78.3":
        parser.error("the native ICU generators must be release 78.3")
    work.mkdir()
    (work / "en.txt").write_text('en { message { "Ember ICU probe" } answer:int { 42 } }\n')
    (work / "resources.txt").write_text("en.res\n")
    for tool, argv in (
            ("genrb", ["-d", work, work / "en.txt"]),
            ("pkgdata", ["-p", "emberprobe", "-m", "common", "-s", work,
                         "-d", work, work / "resources.txt"])):
        result = process.capture([str(prefix / "bin" / tool)] + [str(arg) for arg in argv])
        (work / (tool + ".stdout")).write_bytes(result.stdout)
        (work / (tool + ".stderr")).write_bytes(result.stderr)
    for name in ("en.res", "emberprobe.dat"):
        paths.regular_file(work / name)
        if not (work / name).stat().st_size:
            raise ValueError(f"empty ICU resource fixture: {name}")
    print("PASS: native ICU 78.3 generated target resource fixtures")


if __name__ == "__main__":
    main()
