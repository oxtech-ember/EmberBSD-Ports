#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the cwrapper rules for base include subdirectories in cross builds."""

import argparse
import os
from pathlib import Path
import shlex
import subprocess

PRINT_ARGS = '#!/bin/sh\nfor arg; do printf "%s\\n" "$arg"; done\n'


def query(args, mode, variables):
    argv = [*shlex.split(args.bmake), "-C", str(args.pkgsrc / "net/chrony"),
            "MAKECONF=" + str(args.makeconf), "USE_CROSS_COMPILE=" + mode,
            "WRKOBJDIR=" + str(args.work / "objects"),
            # pkgsrc sets the wrapper transforms after its barrier.
            "_PKGSRC_BARRIER=yes"]
    for variable in variables:
        argv.extend(("-V", "${" + variable + "}"))
    result = subprocess.run(argv, check=True, text=True, capture_output=True)
    values = result.stdout.splitlines()
    if len(values) != len(variables):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    return dict(zip(variables, values))


def wrap(args, name, transforms, words):
    """Run the real cc-wrapper with these rules and return the compiler argv."""
    root = args.work / name
    (root / "config").mkdir(parents=True)
    compiler = root / "print-args"
    compiler.write_text(PRINT_ARGS)
    compiler.chmod(0o755)
    lines = ["worklog=" + str(root / "work.log"), "wrksrc=" + str(root),
             "path=/usr/bin:/bin", "exec_path=" + str(root / "cc"),
             "exec=" + str(compiler)]
    lines += ["transform=" + rule for rule in transforms]
    (root / "config/cc").write_text("\n".join(lines) + "\n")
    env = {"PATH": "/usr/bin:/bin", "CWRAPPERS_CONFIG_DIR": str(root / "config")}
    result = subprocess.run([args.cwrapper, *words], env=env, check=True,
                            text=True, capture_output=True)
    return result.stdout.splitlines()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True, help="Exported pkgsrc tree")
    parser.add_argument("--makeconf", type=Path, required=True, help="Cross MAKECONF")
    parser.add_argument("--bmake", required=True, help="Native BSD make command and options")
    parser.add_argument("--cwrapper", required=True, help="Installed cwrappers cc-wrapper")
    parser.add_argument("--work", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    if not os.path.isabs(args.cwrapper) or not os.access(args.cwrapper, os.X_OK):
        parser.error("--cwrapper must be an absolute executable path")
    args.work.mkdir()
    (args.work / "objects").mkdir()
    names = ("PKG_FAIL_REASON", "_CROSS_DESTDIR", "COMPILER_INCLUDE_DIRS",
             "_CWRAPPERS_TRANSFORM")
    cross = query(args, "yes", names)
    native = query(args, "no", names)
    if cross["PKG_FAIL_REASON"] or native["PKG_FAIL_REASON"]:
        raise AssertionError("chrony metadata rejected")
    root = cross["_CROSS_DESTDIR"]
    if not root.startswith("/") or native["_CROSS_DESTDIR"]:
        raise AssertionError("query did not select a cross and a native case")
    if cross["COMPILER_INCLUDE_DIRS"].split() != ["/usr/include"]:
        raise AssertionError("unexpected cross base include directories")

    # A base subdirectory from BUILDLINK_INCDIRS, and the base directory.
    # The wrapper also removes repeated -I arguments, so each source of the
    # path has its own call.
    target = root + "/usr/include/readline"
    rules = cross["_CWRAPPERS_TRANSFORM"].split()
    out = wrap(args, "cross-incdirs", rules,
               ["-I/usr/include", "-I/usr/include/readline", "-isystem",
                "/usr/include/readline", "-c", "probe.c"])
    if out != ["-I" + target, "-isystem", target, "-c", "probe.c"]:
        raise AssertionError("cross base include arguments: " + repr(out))
    # The same paths from pkg-config with PKG_CONFIG_SYSROOT_DIR.
    out = wrap(args, "cross-pkgconfig", rules,
               ["-I" + root + "/usr/include", "-I" + target, "-c", "probe.c"])
    if out != ["-I" + target, "-c", "probe.c"]:
        raise AssertionError("cross sysroot include arguments: " + repr(out))

    native_dirs = native["COMPILER_INCLUDE_DIRS"].split()
    if not native_dirs:
        raise AssertionError("native case has no base include directory")
    base = native_dirs[0]
    out = wrap(args, "native", native["_CWRAPPERS_TRANSFORM"].split(),
               ["-I" + base, "-I" + base + "/readline", "-c", "probe.c"])
    if out != ["-I" + base + "/readline", "-c", "probe.c"]:
        raise AssertionError("native include arguments changed: " + repr(out))
    print("PASS: cross base include subdirectories use the target sysroot; native unchanged")
    print("No package was built or installed.")


if __name__ == "__main__":
    main()
