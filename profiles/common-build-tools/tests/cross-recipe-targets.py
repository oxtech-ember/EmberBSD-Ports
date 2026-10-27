#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the target settings of the chrony and aravis cross recipes."""

import argparse
from pathlib import Path
import shlex
import subprocess


def query(args, pkgpath, mode, variables):
    argv = [args.bmake, "-C", str(args.pkgsrc / pkgpath),
            "MAKECONF=" + str(args.makeconf), "USE_CROSS_COMPILE=" + mode]
    for variable in variables:
        argv.extend(("-v", variable))
    result = subprocess.run(argv, check=True, text=True, capture_output=True)
    values = result.stdout.splitlines()
    if len(values) != len(variables):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    return dict(zip(variables, values))


def check_chrony(args):
    names = ("PKG_FAIL_REASON", "CONFIGURE_ARGS")
    cross = query(args, "net/chrony", "yes", names)
    native = query(args, "net/chrony", "no", names)
    if cross["PKG_FAIL_REASON"] or native["PKG_FAIL_REASON"]:
        raise AssertionError("chrony metadata rejected")
    words = shlex.split(cross["CONFIGURE_ARGS"])
    for wanted in ("--host-system=NetBSD", "--host-machine=" + args.machine_arch):
        if wanted not in words:
            raise AssertionError("cross chrony configure lacks " + wanted)
    if not any(w.startswith("--host-release=") and w != "--host-release=" for w in words):
        raise AssertionError("cross chrony configure lacks the target release")
    if "--host-" in native["CONFIGURE_ARGS"]:
        raise AssertionError("native chrony configure names a target system")


GLIB_TOOLS = ("glib-mkenums", "glib-compile-resources")
GLIB_DEPENDS = ("glib2>=0:../../devel/glib2", "glib2-tools>=0:../../devel/glib2-tools")


def check_aravis(args):
    names = ["PKG_FAIL_REASON", "TOOLBASE", "TOOL_DEPENDS", "MESON_BINARIES"]
    names += ["MESON_BINARY." + tool for tool in GLIB_TOOLS]
    cross = query(args, "multimedia/aravis", "yes", names)
    native = query(args, "multimedia/aravis", "no", names)
    if cross["PKG_FAIL_REASON"] or native["PKG_FAIL_REASON"]:
        raise AssertionError("aravis metadata rejected")
    for tool in GLIB_TOOLS:
        if tool not in cross["MESON_BINARIES"].split():
            raise AssertionError("cross aravis does not give Meson " + tool)
        if cross["MESON_BINARY." + tool] != cross["TOOLBASE"] + "/bin/" + tool:
            raise AssertionError("cross aravis " + tool + " is not the build host program")
        if tool in native["MESON_BINARIES"].split() or native["MESON_BINARY." + tool]:
            raise AssertionError("native aravis overrides " + tool)
    for depend in GLIB_DEPENDS:
        if depend not in cross["TOOL_DEPENDS"].split():
            raise AssertionError("cross aravis lacks the tool dependency " + depend)
    if GLIB_DEPENDS[0] in native["TOOL_DEPENDS"].split():
        raise AssertionError("native aravis adds a build host glib2")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True, help="Exported pkgsrc tree")
    parser.add_argument("--makeconf", type=Path, required=True, help="Cross MAKECONF")
    parser.add_argument("--bmake", required=True, help="Native BSD make command")
    parser.add_argument("--machine-arch", default="aarch64")
    parser.add_argument("--work", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    args.work.mkdir()
    check_chrony(args)
    check_aravis(args)
    print("PASS: chrony names its target system; cross aravis runs build host GLib tools")
    print("No package was built or installed.")


if __name__ == "__main__":
    main()
