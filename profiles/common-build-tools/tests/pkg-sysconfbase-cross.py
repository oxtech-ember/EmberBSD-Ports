#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that a cross build keeps the target configuration directory.

The build host part of a shared mk.conf sets PKG_SYSCONFBASE to the build
host prefix. Before the fix a cross print/libpaper used that directory for
PKG_SYSCONFDIR and --sysconfdir, and the target library looked for its
configuration in a build host path.
"""

import argparse
import os
from pathlib import Path
import subprocess

VARIABLES = ("OPSYS", "PREFIX", "PKG_SYSCONFDIR", "CONFIGURE_ARGS")
HOST_BASE = "/nonexistent-build-host/etc"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()

    pkgsrc = args.pkgsrc.resolve(strict=True)
    makeconf = args.makeconf.resolve(strict=True)
    work = args.work.resolve()
    if work.exists():
        parser.error("Work directory already exists")
    work.mkdir(parents=True)
    wrapper = work / "mk.conf"
    wrapper.write_text("PKG_SYSCONFBASE=\t%s\n.include \"%s\"\n" %
                       (HOST_BASE, makeconf))

    argv = [args.bmake, "-C", str(pkgsrc / "print/libpaper"),
            "MAKECONF=" + str(wrapper)]
    for variable in VARIABLES:
        argv.extend(("-v", variable))
    result = subprocess.run(argv, check=True, text=True,
                            env=dict(os.environ, MAKECONF=str(wrapper)),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    (work / "libpaper.log").write_text(result.stdout)
    values = dict(zip(VARIABLES, result.stdout.splitlines()))
    if len(values) != len(VARIABLES):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    if values["OPSYS"] == "Darwin":
        parser.error("Select a cross MAKECONF for a non-Darwin target")

    expected = values["PREFIX"] + "/etc"
    failures = []
    if values["PKG_SYSCONFDIR"] != expected:
        failures.append("PKG_SYSCONFDIR is %s, not %s" %
                        (values["PKG_SYSCONFDIR"], expected))
    if "--sysconfdir=" + expected not in values["CONFIGURE_ARGS"].split():
        failures.append("configure does not get --sysconfdir=" + expected)
    if HOST_BASE in values["CONFIGURE_ARGS"]:
        failures.append("configure gets the build host configuration base")
    if failures:
        for failure in failures:
            print("FAIL: " + failure)
        raise SystemExit(1)
    print("PASS: libpaper for %s uses %s" % (values["OPSYS"], expected))


if __name__ == "__main__":
    main()
