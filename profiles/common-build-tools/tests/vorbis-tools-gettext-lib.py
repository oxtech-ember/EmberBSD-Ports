#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that audio/vorbis-tools depends on gettext-lib without a built-in libintl.

Before the fix a native macOS build linked the installed libintl, and
check-shlibs stopped: gettext-lib was not a runtime dependency.
"""

import argparse
import os
from pathlib import Path
import subprocess

VARIABLES = ("USE_BUILTIN.gettext", "DEPENDS")


def query(args, makeconf, *extra):
    argv = [args.bmake, "-C", str(args.pkgsrc.resolve(strict=True) / "audio/vorbis-tools"),
            "MAKECONF=" + str(makeconf), *extra]
    for variable in VARIABLES:
        argv.extend(("-V", "${%s}" % variable))
    result = subprocess.run(argv, check=True, text=True,
                            env=dict(os.environ, MAKECONF=str(makeconf)),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    values = result.stdout.splitlines()
    if len(values) != len(VARIABLES):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    builtin, depends = values
    gettext = [d for d in depends.split() if d.endswith("../../devel/gettext-lib")]
    return builtin.lower() == "yes", gettext


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True,
                        help="MAKECONF of a NetBSD cross build on macOS")
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()
    makeconf = args.makeconf.resolve(strict=True)
    builtin, gettext = query(args, makeconf, "USE_CROSS_COMPILE=no")
    if builtin or not gettext:
        print("FAIL: native vorbis-tools lacks the gettext-lib dependency")
        raise SystemExit(1)
    builtin, gettext = query(args, makeconf)
    if not builtin or gettext:
        print("FAIL: NetBSD vorbis-tools does not use the built-in libintl")
        raise SystemExit(1)
    print("PASS: vorbis-tools depends on gettext-lib only without a built-in libintl")


if __name__ == "__main__":
    main()
