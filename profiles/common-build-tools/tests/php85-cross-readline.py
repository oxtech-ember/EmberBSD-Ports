#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that a cross lang/php85 looks for readline in the buildlink tree.

Before the fix configure looked for /usr/pkg/include/readline/readline.h
on the build host and stopped with "Please reinstall readline".
"""

import argparse
import os
from pathlib import Path
import shlex
import subprocess

VARIABLES = ("BUILDLINK_DIR", "BUILDLINK_PREFIX.readline", "CONFIGURE_ARGS")


def query(args, makeconf, *extra):
    argv = [args.bmake, "-C", str(args.pkgsrc.resolve(strict=True) / "lang/php85"),
            "MAKECONF=" + str(makeconf), "PKG_OPTIONS.php=readline", *extra]
    for variable in VARIABLES:
        argv.extend(("-V", "${%s}" % variable))
    result = subprocess.run(argv, check=True, text=True,
                            env=dict(os.environ, MAKECONF=str(makeconf)),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    values = result.stdout.splitlines()
    if len(values) != len(VARIABLES):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    buildlink, prefix, flags = values
    readline = [word for word in shlex.split(flags) if word.startswith("--with-readline")]
    return buildlink, prefix, readline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True,
                        help="MAKECONF of a cross build")
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()
    makeconf = args.makeconf.resolve(strict=True)
    buildlink, _, readline = query(args, makeconf)
    if readline != ["--with-readline=" + buildlink]:
        print("FAIL: cross php85 passes %r, not the buildlink tree" % readline)
        raise SystemExit(1)
    _, prefix, readline = query(args, makeconf, "USE_CROSS_COMPILE=no")
    if readline != ["--with-readline=" + prefix]:
        print("FAIL: native php85 passes %r, not the readline prefix" % readline)
        raise SystemExit(1)
    print("PASS: cross php85 finds readline in the buildlink tree")


if __name__ == "__main__":
    main()
