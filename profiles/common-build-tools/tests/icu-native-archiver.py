#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that a native textproc/icu configures the selected archiver.

The selected native toolset PATH holds only the Ports prefix, which has
llvm-ar but no "ar". ICU's configure looked for "ar" on PATH, set AR to
false, and the native TOOL_DEPENDS build for a cross icu stopped at
libicudata.a. The test configures the recipe natively in its own
WRKOBJDIR and checks the archiver configure recorded.
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
    recipe = args.pkgsrc.resolve(strict=True) / "textproc/icu"
    base = [args.bmake, "-C", str(recipe), "MAKECONF=" + str(makeconf),
            "WRKOBJDIR=" + str(work / "obj"), "USE_CROSS_COMPILE=no"]
    env = dict(os.environ, MAKECONF=str(makeconf))
    query = subprocess.run(base + ["-v", "WRKSRC", "-v", "AR"], check=True,
                           text=True, env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    wrksrc, selected = query.stdout.split()
    with open(work / "configure.log", "w") as log:
        subprocess.run(base + ["configure"], env=env, stdin=subprocess.DEVNULL,
                       stdout=log, stderr=subprocess.STDOUT)
    makefile = Path(wrksrc) / "icudefs.mk"
    if not makefile.exists():
        print("FAIL: configure did not create %s" % makefile)
        raise SystemExit(1)
    match = re.search(r"^AR\s*=\s*(\S+)", makefile.read_text(errors="replace"),
                      re.MULTILINE)
    recorded = match.group(1) if match else ""
    if recorded != selected:
        print("FAIL: icudefs.mk AR=%r, selected %r" % (recorded, selected))
        raise SystemExit(1)
    print("PASS: native icu archives with %s" % recorded)


if __name__ == "__main__":
    main()
