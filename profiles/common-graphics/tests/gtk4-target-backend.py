#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that a cross x11/gtk4 selects its backends for the target.

Run on a macOS build host, which has the Quartz framework, with a cross
MAKECONF for a NetBSD target. Before the fix the recipe offered only the
Quartz backend and refused the wayland option that devel/wayland/platform.mk
suggests for NetBSD.
"""

import argparse
import os
from pathlib import Path
import subprocess

VARIABLES = ("PKG_FAIL_REASON", "OPSYS", "PKG_SUPPORTED_OPTIONS", "PKG_OPTIONS",
             "MESON_ARGS")
QUARTZ = Path("/System/Library/Frameworks/Quartz.framework")


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
    if not QUARTZ.exists():
        parser.error("Run on a build host with " + str(QUARTZ))
    work.mkdir(parents=True)

    argv = [args.bmake, "-C", str(pkgsrc / "x11/gtk4"), "MAKECONF=" + str(makeconf)]
    for variable in VARIABLES:
        argv.extend(("-v", variable))
    result = subprocess.run(argv, check=True, text=True,
                            env=dict(os.environ, MAKECONF=str(makeconf)),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    (work / "gtk4.log").write_text(result.stdout)
    values = dict(zip(VARIABLES, result.stdout.splitlines()))
    if len(values) != len(VARIABLES):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    if values["OPSYS"] == "Darwin":
        parser.error("Select a cross MAKECONF for a non-Darwin target")

    failures = []
    if "options are not supported" in values["PKG_FAIL_REASON"] or \
            "not supported: wayland" in values["PKG_FAIL_REASON"]:
        failures.append("option refusal: " + values["PKG_FAIL_REASON"])
    supported = values["PKG_SUPPORTED_OPTIONS"].split()
    options = values["PKG_OPTIONS"].split()
    meson = values["MESON_ARGS"].split()
    if "quartz" in supported or "quartz" in options:
        failures.append("the build host Quartz backend is offered to the target")
    if "wayland" not in supported:
        failures.append("the wayland option is not offered to the target")
    if "x11" not in options or "-Dx11-backend=true" not in meson:
        failures.append("the X11 backend is not selected")
    if "-Dmacos-backend=false" not in meson:
        failures.append("the macOS backend is not disabled")
    if failures:
        for failure in failures:
            print("FAIL: " + failure)
        raise SystemExit(1)
    print("PASS: gtk4 for %s offers %s and selects %s" %
          (values["OPSYS"], " ".join(supported), " ".join(options)))


if __name__ == "__main__":
    main()
