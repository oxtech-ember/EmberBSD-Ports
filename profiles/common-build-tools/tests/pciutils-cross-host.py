#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that a cross sysutils/pciutils names the target to lib/configure.

Before the fix MAKE_FLAGS had no HOST, and lib/configure described the
build host with uname: a build on macOS compiled darwin.c for NetBSD.
"""

import argparse
import os
from pathlib import Path
import subprocess

RECIPE = "sysutils/pciutils"
VARIABLES = ("OPSYS", "LOWER_OPSYS", "MACHINE_ARCH", "OS_VERSION", "MAKE_FLAGS")


def query(args, recipe):
    argv = [args.bmake, "-C", str(args.pkgsrc.resolve(strict=True) / recipe),
            "MAKECONF=" + str(args.makeconf.resolve(strict=True))]
    for variable in VARIABLES:
        argv.extend(("-v", variable))
    result = subprocess.run(argv, check=True, text=True,
                            env=dict(os.environ, MAKECONF=str(args.makeconf.resolve())),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    values = dict(zip(VARIABLES, result.stdout.splitlines()))
    if len(values) != len(VARIABLES):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    return result.stdout, values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    if work.exists():
        parser.error("Work directory already exists")
    work.mkdir(parents=True)
    output, values = query(args, RECIPE)
    (work / "query.log").write_text(output)
    if values["OPSYS"] == "Darwin":
        parser.error("Select a cross MAKECONF for a non-Darwin target")
    flags = values["MAKE_FLAGS"].split()
    expected = ["HOST=%s-%s" % (values["MACHINE_ARCH"], values["LOWER_OPSYS"]),
                "RELEASE=" + values["OS_VERSION"]]
    missing = [flag for flag in expected if flag not in flags]
    if not any(flag.startswith("AR=") for flag in flags):
        missing.append("AR=<target archiver>")
    if missing:
        print("FAIL: MAKE_FLAGS lacks " + " ".join(missing))
        raise SystemExit(1)
    print("PASS: pciutils for %s gets %s" % (values["OPSYS"], " ".join(expected)))


if __name__ == "__main__":
    main()
