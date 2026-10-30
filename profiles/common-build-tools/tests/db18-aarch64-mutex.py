#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that databases/db18 configures a mutex for an AArch64 NetBSD target.

NetBSD pthread mutexes cannot be shared between processes, so configure
skips the POSIX choices. Before the fix the ARM64 test only accepted the
Apple __arm64__ macro, configure chose the removed fcntl mutexes and
stopped. The test configures the recipe in its own WRKOBJDIR.
"""

import argparse
import os
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()
    makeconf = args.makeconf.resolve(strict=True)
    work = args.work.resolve()
    if work.exists():
        parser.error("Work directory already exists")
    work.mkdir(parents=True)
    recipe = args.pkgsrc.resolve(strict=True) / "databases/db18"
    base = [args.bmake, "-C", str(recipe), "MAKECONF=" + str(makeconf),
            "WRKOBJDIR=" + str(work / "obj")]
    env = dict(os.environ, MAKECONF=str(makeconf))
    query = subprocess.run(base + ["-v", "OPSYS", "-v", "MACHINE_ARCH"], check=True,
                           text=True, env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    opsys, arch = query.stdout.split()
    if (opsys, arch) != ("NetBSD", "aarch64"):
        parser.error("Select a cross MAKECONF for an aarch64 NetBSD target")
    with open(work / "configure.log", "w") as log:
        subprocess.run(base + ["configure"], env=env, stdin=subprocess.DEVNULL,
                       stdout=log, stderr=subprocess.STDOUT)
    text = (work / "configure.log").read_text(errors="replace")
    found = re.findall(r"checking for mutexes\.\.\. (\S+)", text)
    if found != ["ARM64/gcc-assembly"]:
        print("FAIL: configure selected %s" % (", ".join(found) or "no mutex"))
        raise SystemExit(1)
    print("PASS: db18 for %s-%s selects %s" % (opsys, arch, found[0]))


if __name__ == "__main__":
    main()
