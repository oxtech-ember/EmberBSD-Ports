#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check qtermwidget's host-tool routing in native and cross pkgsrc modes."""
import argparse
import os
from pathlib import Path
import subprocess


def query(bmake, recipe, makeconf, mode):
    names = ("PKGNAME", "PKG_FAIL_REASON", "TOOL_DEPENDS", "CMAKE_CONFIGURE_ARGS",
             "EMBERBSD_LXQT_HOST_TOOLS", "EMBERBSD_QT_HOST_PATH", "TOOLBASE")
    argv = [bmake, "-C", str(recipe), "_MAKEVARS_MK=defined", "_PKGSRC_BARRIER=yes",
            "USE_CROSS_COMPILE=" + mode]
    for name in names:
        argv.extend(("-v", name))
    result = subprocess.run(argv, env={**os.environ, "MAKECONF": str(makeconf)},
                            check=True, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    lines = result.stdout.splitlines()
    if len(lines) != len(names):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    return dict(zip(names, lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True)
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()
    recipe = args.pkgsrc.resolve(strict=True) / "x11/qtermwidget"
    makeconf = args.makeconf.resolve(strict=True)

    cross = query(args.bmake, recipe, makeconf, "yes")
    if cross["PKGNAME"] != "qtermwidget-2.5.0":
        raise RuntimeError("Wrong cross package identity: " + cross["PKGNAME"])
    if cross["PKG_FAIL_REASON"]:
        raise RuntimeError("Cross host-tool prerequisites failed: " + cross["PKG_FAIL_REASON"])
    modules = cross["EMBERBSD_LXQT_HOST_TOOLS"]
    qt = cross["EMBERBSD_QT_HOST_PATH"]
    prefix = cross["TOOLBASE"]
    cmake_args = cross["CMAKE_CONFIGURE_ARGS"].split()
    deps = cross["TOOL_DEPENDS"].split()
    if bool(modules) == any(dep.startswith("lxqt-build-tools") for dep in deps):
        raise RuntimeError("LXQt build-tool dependency does not match the selected prefix")
    if bool(qt) == any(dep.startswith("qt6-qttools") for dep in deps):
        raise RuntimeError("Qt Linguist tool dependency does not match the selected prefix")
    module_arg = "-Dlxqt2-build-tools_DIR=" + (modules or prefix) + "/share/cmake/lxqt2-build-tools"
    if module_arg not in cmake_args:
        raise RuntimeError("Cross build does not select the native LXQt modules")
    qt_arg = ("-DQt6LinguistTools_DIR=" + qt if qt else "-DQt6LinguistTools_DIR:PATH=" + prefix + "/qt6")
    if qt_arg + "/lib/cmake/Qt6LinguistTools" not in cmake_args:
        raise RuntimeError("Cross build does not select the native Qt LinguistTools")

    native = query(args.bmake, recipe, makeconf, "no")
    for dependency in ("lxqt-build-tools>=2.5.0", "qt6-qttools-"):
        if dependency not in native["TOOL_DEPENDS"]:
            raise RuntimeError("Native build lost its upstream tool dependency: " + dependency)
    if "lxqt-build-tools_DIR" in native["CMAKE_CONFIGURE_ARGS"] or "Qt6LinguistTools_DIR=" in native["CMAKE_CONFIGURE_ARGS"]:
        raise RuntimeError("Native build inherited cross host-tool overrides")

    print("PASS: qtermwidget uses the selected LXQt and Qt host tools in both package roles")


if __name__ == "__main__":
    main()
