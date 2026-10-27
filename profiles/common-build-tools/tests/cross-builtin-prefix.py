#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the root of built-in packages in cross and native metadata."""

import argparse
from pathlib import Path
import shlex
import subprocess

# Base providers of the EmberBSD target that the cross profile selects.
CROSS_BUILTINS = {
    "net/chrony": ("editline", "gettext", "iconv", "termcap"),
    "lang/python315": ("bzip2", "curses", "xz"),
}
# A host value that a cross build must ignore, also on a command line.
FOREIGN_SDK = "/nonexistent/EmberBSD-test/MacOSX.sdk"


def query(args, pkgpath, mode, variables, extra=()):
    argv = [*shlex.split(args.bmake), "-C", str(args.pkgsrc / pkgpath),
            "MAKECONF=" + str(args.makeconf), "USE_CROSS_COMPILE=" + mode,
            "WRKOBJDIR=" + str(args.work / "objects"),
            # pkgsrc sets built-in prefixes after its barrier.
            "_PKGSRC_BARRIER=yes", *extra]
    for variable in variables:
        argv.extend(("-V", "${" + variable + "}"))
    result = subprocess.run(argv, check=True, text=True, capture_output=True)
    values = result.stdout.splitlines()
    if len(values) != len(variables):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    return dict(zip(variables, values))


def check_cross(args, pkgpath, builtins):
    names = ["PKG_FAIL_REASON", "OPSYS", "OSX_SDK_PATH", "BUILDLINK_CPPFLAGS",
             "BUILDLINK_LDFLAGS"]
    for name in builtins:
        names += ["USE_BUILTIN." + name, "BUILDLINK_PREFIX." + name]
    # A command-line value has the highest precedence. The fix must hold
    # without a profile that hides a host OSX_SDK_PATH.
    cross = query(args, pkgpath, "yes", names, ("OSX_SDK_PATH=" + FOREIGN_SDK,))
    if cross["PKG_FAIL_REASON"]:
        raise AssertionError(pkgpath + " cross metadata rejected: " + cross["PKG_FAIL_REASON"])
    if cross["OPSYS"] != "NetBSD" or cross["OSX_SDK_PATH"] != FOREIGN_SDK:
        raise AssertionError(pkgpath + " query did not select the cross case")
    for name in builtins:
        if cross["USE_BUILTIN." + name] != "yes":
            raise AssertionError(pkgpath + " does not use the base " + name)
        if cross["BUILDLINK_PREFIX." + name] != "/usr":
            raise AssertionError(pkgpath + " roots the base " + name + " in " +
                                 repr(cross["BUILDLINK_PREFIX." + name]))
    for flags in ("BUILDLINK_CPPFLAGS", "BUILDLINK_LDFLAGS"):
        if FOREIGN_SDK in cross[flags]:
            raise AssertionError(pkgpath + " " + flags + " contains the host SDK")
    return cross


def check_native(args):
    names = ("PKG_FAIL_REASON", "NATIVE_OPSYS", "OPSYS", "TOOLS_CROSS_DESTDIR",
             "OSX_SDK_PATH", "USE_BUILTIN.iconv", "BUILDLINK_PREFIX.iconv")
    native = query(args, "net/chrony", "no", names)
    if native["NATIVE_OPSYS"] != "Darwin":
        return "native Darwin check skipped on " + native["NATIVE_OPSYS"]
    if native["PKG_FAIL_REASON"]:
        raise AssertionError("native chrony metadata rejected: " + native["PKG_FAIL_REASON"])
    if native["OPSYS"] != "Darwin" or native["TOOLS_CROSS_DESTDIR"]:
        raise AssertionError("native query selected a cross target")
    if not native["OSX_SDK_PATH"].startswith("/"):
        raise AssertionError("native Darwin metadata has no absolute OSX_SDK_PATH")
    if native["USE_BUILTIN.iconv"] != "yes":
        raise AssertionError("native Darwin does not use the SDK iconv")
    if native["BUILDLINK_PREFIX.iconv"] != native["OSX_SDK_PATH"] + "/usr":
        raise AssertionError("native Darwin iconv left the SDK: " +
                             repr(native["BUILDLINK_PREFIX.iconv"]))
    return "native Darwin keeps the SDK root"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True, help="Exported pkgsrc tree")
    parser.add_argument("--makeconf", type=Path, required=True, help="Cross MAKECONF")
    parser.add_argument("--bmake", required=True, help="Native BSD make command and options")
    parser.add_argument("--work", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    args.work.mkdir()
    (args.work / "objects").mkdir()
    for pkgpath, builtins in CROSS_BUILTINS.items():
        cross = check_cross(args, pkgpath, builtins)
        if pkgpath == "net/chrony" and \
                "-I/usr/include/readline" not in cross["BUILDLINK_CPPFLAGS"].split():
            raise AssertionError("cross chrony lacks the base readline include directory")
    native = check_native(args)
    if any((args.work / "objects").iterdir()):
        raise AssertionError("a metadata query wrote into WRKOBJDIR")
    print("PASS: cross built-in packages use the target root; " + native)
    print("No package was built or installed.")


if __name__ == "__main__":
    main()
