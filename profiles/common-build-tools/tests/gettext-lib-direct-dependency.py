#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that a package depends on gettext-lib only without a built-in libintl.

Packages that link glib2 load libintl directly on macOS, because
glib-2.0.pc lists -lintl in Libs. Without a gettext-lib dependency
check-shlibs stops the native build: gettext-lib is not a runtime
dependency. On NetBSD libintl is built in and no dependency is added.
"""

import argparse
import os
from pathlib import Path
import subprocess

VARIABLES = ("USE_BUILTIN.gettext", "DEPENDS")


def query(args, makeconf, *extra):
    argv = [args.bmake, "-C", str(args.pkgsrc.resolve(strict=True) / args.pkgpath),
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
    parser.add_argument("--pkgpath", required=True, help="for example graphics/gts")
    parser.add_argument("--makeconf", type=Path, required=True,
                        help="MAKECONF of a NetBSD cross build on macOS")
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()
    makeconf = args.makeconf.resolve(strict=True)
    builtin, gettext = query(args, makeconf, "USE_CROSS_COMPILE=no")
    if builtin or not gettext:
        print("FAIL: native %s lacks the gettext-lib dependency" % args.pkgpath)
        raise SystemExit(1)
    builtin, gettext = query(args, makeconf)
    if not builtin or gettext:
        print("FAIL: NetBSD %s does not use the built-in libintl" % args.pkgpath)
        raise SystemExit(1)
    print("PASS: %s depends on gettext-lib only without a built-in libintl" % args.pkgpath)


if __name__ == "__main__":
    main()
