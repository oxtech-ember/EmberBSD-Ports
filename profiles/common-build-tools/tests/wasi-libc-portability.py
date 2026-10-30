#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that a native lang/wasi-libc passes the pkgsrc portability check.

Cross configurations set PKG_DEVELOPER=yes, so the native TOOL_DEPENDS
build of wasi-libc (for llhttp-wasi and undici) ran check-portability.
The unused upstream test/open-posix-test-suite scripts use "==" in
test(1), and the check stopped the build. The test configures the
recipe natively in its own WRKOBJDIR.
"""

import argparse
import os
from pathlib import Path
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
    recipe = args.pkgsrc.resolve(strict=True) / "lang/wasi-libc"
    base = [args.bmake, "-C", str(recipe), "MAKECONF=" + str(makeconf),
            "WRKOBJDIR=" + str(work / "obj"), "USE_CROSS_COMPILE=no",
            "PKG_DEVELOPER=yes"]
    env = dict(os.environ, MAKECONF=str(makeconf))
    with open(work / "configure.log", "w") as log:
        result = subprocess.run(base + ["configure"], env=env,
                                stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT)
    text = (work / "configure.log").read_text(errors="replace")
    if "[check-portability.awk]" in text and "ERROR" in text:
        print("FAIL: check-portability rejected wasi-libc")
        raise SystemExit(1)
    if "Checking for portability problems" not in text or result.returncode:
        print("FAIL: configure did not reach or pass the portability check")
        raise SystemExit(1)
    print("PASS: native wasi-libc passes check-portability")


if __name__ == "__main__":
    main()
