#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that a cross textproc/enca records the target mktemp.

Before the fix configure found the build host mktemp on PATH, and the
installed extconv scripts named it, so check-wrkref stopped the package.
"""

import argparse
import os
from pathlib import Path
import subprocess

VARIABLES = ("OPSYS", "CONFIGURE_ENV")
TARGET_MKTEMP = {"NetBSD": "/usr/bin/mktemp"}


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
    argv = [args.bmake, "-C", str(args.pkgsrc.resolve(strict=True) / "textproc/enca"),
            "MAKECONF=" + str(makeconf)]
    for variable in VARIABLES:
        argv.extend(("-v", variable))
    result = subprocess.run(argv, check=True, text=True,
                            env=dict(os.environ, MAKECONF=str(makeconf)),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    (work / "enca.log").write_text(result.stdout)
    values = dict(zip(VARIABLES, result.stdout.splitlines()))
    if len(values) != len(VARIABLES):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    if values["OPSYS"] not in TARGET_MKTEMP:
        parser.error("Select a cross MAKECONF for a NetBSD target")
    expected = "ac_cv_path_MKTEMP_PROG=" + TARGET_MKTEMP[values["OPSYS"]]
    if expected not in values["CONFIGURE_ENV"].split():
        print("FAIL: CONFIGURE_ENV lacks " + expected)
        raise SystemExit(1)
    print("PASS: enca for %s gets %s" % (values["OPSYS"], expected))


if __name__ == "__main__":
    main()
