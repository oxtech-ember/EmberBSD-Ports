#!/usr/bin/env python3
"""Build the shared groff 1.24.2 native tbl generator for package manuals."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--cxx", default="c++")
    parser.add_argument("--make", default="gmake")
    args = parser.parse_args()
    args.archive = args.archive.resolve()
    args.work = args.work.absolute()
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != "f9c1efd5bebbe37fc6e1063db7473ce8df1e3e0be4ff0f43ce04fce57e9c5dd9":
        parser.error("the common groff 1.24.2 archive SHA256 differs")
    if args.work.exists():
        parser.error("work directory already exists")
    args.work.mkdir(parents=True)
    temp = args.work / "tmp"
    temp.mkdir()
    environment = dict(os.environ, TMPDIR=str(temp), CC=args.cc, CXX=args.cxx)
    with tarfile.open(args.archive) as archive:
        archive.extractall(args.work, filter="data")
    source = args.work / "groff-1.24.2"
    patches = Path(__file__).resolve().parents[2] / "profiles/common-build-tools/recipes/textproc/groff/patches"
    for patch in sorted(patches.glob("patch-*")):
        with patch.open() as data, (args.work / (patch.name + ".log")).open("w") as log:
            subprocess.run(["patch", "-f", "-F0", "-p0"], cwd=source,
                           stdin=data, stdout=log, stderr=subprocess.STDOUT, check=True)
    objects = args.work / "objects"
    objects.mkdir()
    with (args.work / "configure.log").open("w") as log:
        subprocess.run([str(source / "configure"), "--prefix=" + str(args.work / "prefix")],
                       cwd=objects, env=environment, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    # Direct Automake binary targets do not depend on BUILT_SOURCES.
    # Generate the complete upstream header set before compiling tbl.
    (objects / "native-tbl.mk").write_text(
        ".PHONY: ember-native-tbl-headers\n"
        "ember-native-tbl-headers: $(BUILT_SOURCES)\n")
    with (args.work / "build.log").open("w") as log:
        subprocess.run([args.make, "-j1", "-f", "Makefile", "-f", "native-tbl.mk",
                        "ember-native-tbl-headers", "tbl"], cwd=objects,
                       env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
    tool = objects / "tbl"
    valid = subprocess.run([tool], input=".TS\nl l.\none\ttwo\n.TE\n",
                           text=True, capture_output=True, check=True)
    if "one" not in valid.stdout or "two" not in valid.stdout:
        raise RuntimeError("tbl did not retain the two input cells")
    invalid = subprocess.run([tool], input=".TS\nq.\none\n.TE\n",
                             text=True, capture_output=True)
    if invalid.returncode == 0:
        raise RuntimeError("tbl accepted the invalid format control")
    (args.work / "valid.roff").write_text(valid.stdout)
    (args.work / "invalid.log").write_text(invalid.stderr)
    print(tool)
    print("Set TOOLS_PLATFORM.tbl to this native executable.")


if __name__ == "__main__":
    main()
