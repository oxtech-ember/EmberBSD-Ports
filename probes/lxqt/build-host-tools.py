#!/usr/bin/env python3
"""Prepare LXQt CMake and translation modules for the common Qt6 cross build."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("host_qt", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("--cmake", default="cmake")
    parser.add_argument("--ninja", default="ninja")
    parser.add_argument("--patch", default="gpatch")
    args = parser.parse_args()
    args.archive = args.archive.resolve()
    args.host_qt = args.host_qt.resolve()
    args.work = args.work.absolute()
    expected = "eeeeb7dbc2271238306139e660acabe4124b3ebab5434e1e40b1f08cf5bcd4ce"
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != expected:
        parser.error("LXQt 2.5.0 archive SHA256 differs")
    if not (args.host_qt / "bin/lrelease").is_file():
        parser.error("the selected Qt6 host prefix has no lrelease")
    if args.work.exists():
        parser.error("work directory already exists")
    args.work.mkdir(parents=True)
    with tarfile.open(args.archive) as archive:
        archive.extractall(args.work, filter="data")
    source = args.work / "lxqt-build-tools-2.5.0"
    patches = Path(__file__).resolve().parent / "recipes/devel/lxqt-build-tools/patches"
    for patch in sorted(patches.glob("patch-*")):
        with patch.open("rb") as source_patch:
            subprocess.run([args.patch, "-p0", "--forward"], cwd=source, stdin=source_patch, check=True)
    objects = args.work / "objects"
    commands = [
        [args.cmake, "-S", str(source), "-B", str(objects), "-G", "Ninja",
         "-DCMAKE_MAKE_PROGRAM=" + args.ninja,
         "-DCMAKE_PREFIX_PATH=" + str(args.host_qt),
         "-DCMAKE_INSTALL_PREFIX=/usr/pkg", "-DLXQT_ETC_XDG_DIR=/usr/pkg/etc/xdg"],
        [args.cmake, "--build", str(objects), "--parallel", "1"],
        [args.cmake, "--install", str(objects)],
    ]
    environment = os.environ.copy()
    environment["DESTDIR"] = str(args.work / "stage")
    (args.work / "tmp").mkdir()
    environment["TMPDIR"] = str(args.work / "tmp")
    for number, command in enumerate(commands):
        with (args.work / f"{number}.log").open("w") as log:
            subprocess.run(command, env=environment, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
    prefix = args.work / "stage/usr/pkg"
    print(prefix)
    print("Set EMBERBSD_LXQT_HOST_TOOLS to this prefix.")


if __name__ == "__main__":
    main()
