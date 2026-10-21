#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the LXQt panel host-tool route in native and cross pkgsrc modes."""

import argparse
import os
from pathlib import Path
import subprocess


VARIABLES = (
    "PKGNAME",
    "PKG_FAIL_REASON",
    "TOOL_DEPENDS",
    "CMAKE_CONFIGURE_ARGS",
    "EMBERBSD_LXQT_HOST_TOOLS",
    "EMBERBSD_QT_HOST_PATH",
    "EMBERBSD_QT_WAYLAND_HOST_PATH",
)


def query(bmake, recipe, makeconf, mode, wayland_host):
    argv = [
        bmake,
        "-C",
        str(recipe),
        "_MAKEVARS_MK=defined",
        "_PKGSRC_BARRIER=yes",
        "USE_CROSS_COMPILE=" + mode,
        "EMBERBSD_QT_WAYLAND_HOST_PATH=" + wayland_host,
    ]
    for variable in VARIABLES:
        argv.extend(("-v", variable))
    result = subprocess.run(
        argv,
        env={**os.environ, "MAKECONF": str(makeconf)},
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    values = result.stdout.splitlines()
    if len(values) != len(VARIABLES):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    return dict(zip(VARIABLES, values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True)
    parser.add_argument("--wayland-host", required=True)
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()
    pkgsrc = args.pkgsrc.resolve(strict=True)
    recipe = pkgsrc / "x11/lxqt-panel"
    makeconf = args.makeconf.resolve(strict=True)

    cross = query(args.bmake, recipe, makeconf, "yes", args.wayland_host)
    if cross["PKGNAME"] != "lxqt-panel-2.4.1nb3":
        raise RuntimeError("Wrong cross package identity: " + cross["PKGNAME"])
    if cross["PKG_FAIL_REASON"]:
        raise RuntimeError("Cross host-tool prerequisites failed: " + cross["PKG_FAIL_REASON"])
    if "lxqt-build-tools" in cross["TOOL_DEPENDS"] or "qt6-qttools" in cross["TOOL_DEPENDS"]:
        raise RuntimeError("Cross build still selects pkgsrc LXQt or Qt host packages")

    lxqt_host = cross["EMBERBSD_LXQT_HOST_TOOLS"]
    qt_host = cross["EMBERBSD_QT_HOST_PATH"]
    wayland_host = cross["EMBERBSD_QT_WAYLAND_HOST_PATH"]
    if (
        not lxqt_host
        or "-Dlxqt2-build-tools_DIR="
        + lxqt_host
        + "/share/cmake/lxqt2-build-tools"
        not in cross["CMAKE_CONFIGURE_ARGS"]
    ):
        raise RuntimeError("Cross build does not select the staged LXQt modules")
    if (
        not qt_host
        or "-DQt6LinguistTools_DIR=" + qt_host + "/lib/cmake/Qt6LinguistTools"
        not in cross["CMAKE_CONFIGURE_ARGS"]
    ):
        raise RuntimeError("Cross build does not select the matching Qt LinguistTools")
    if (
        not wayland_host
        or "-DQt6WaylandScannerTools_DIR:PATH="
        + wayland_host
        + "/lib/cmake/Qt6WaylandScannerTools"
        not in cross["CMAKE_CONFIGURE_ARGS"]
    ):
        raise RuntimeError("Cross build does not select the matching native Qt Wayland scanner")

    native = query(args.bmake, recipe, makeconf, "no", args.wayland_host)
    for dependency in ("lxqt-build-tools>=2.4.0", "qt6-qttools-"):
        if dependency not in native["TOOL_DEPENDS"]:
            raise RuntimeError("Native build lost its upstream tool dependency: " + dependency)
    if (
        "lxqt2-build-tools_DIR" in native["CMAKE_CONFIGURE_ARGS"]
        or "Qt6LinguistTools_DIR=" in native["CMAKE_CONFIGURE_ARGS"]
        or "Qt6WaylandScannerTools_DIR" in native["CMAKE_CONFIGURE_ARGS"]
    ):
        raise RuntimeError("Native build inherited cross host-tool overrides")

    missing_wayland = query(args.bmake, recipe, makeconf, "yes", "")
    if "EMBERBSD_QT_WAYLAND_HOST_PATH" not in missing_wayland["PKG_FAIL_REASON"]:
        raise RuntimeError("Cross build did not reject a missing native Qt Wayland scanner")

    print("PASS: lxqt-panel uses staged host tools only in cross mode")


if __name__ == "__main__":
    main()
