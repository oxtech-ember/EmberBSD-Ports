#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that cross packages use a staged target Perl for runtime scripts."""

import argparse
from pathlib import Path
import subprocess


VARIABLES = ("PKG_FAIL_REASON", "DEPENDS", "PERL5")


def query(bmake, recipe, makeconf, sysroot, mode):
    argv = [
        bmake,
        "-C",
        str(recipe),
        "MAKECONF=" + str(makeconf),
        "USE_CROSS_COMPILE=" + mode,
        "EMBERBSD_CROSS_SYSROOT=" + str(sysroot),
    ]
    for variable in VARIABLES:
        argv.extend(("-v", variable))
    result = subprocess.run(
        argv, check=True, text=True, stdout=subprocess.PIPE,
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
    parser.add_argument("--sysroot", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()

    pkgsrc = args.pkgsrc.resolve(strict=True)
    makeconf = args.makeconf.resolve(strict=True)
    sysroot = args.sysroot.resolve(strict=True)
    work = args.work.resolve()
    if work.exists():
        parser.error("Work directory already exists")
    if not (sysroot / "usr/pkg/bin/perl").is_file():
        parser.error("Sysroot must contain the target Perl package")
    work.mkdir(parents=True)
    recipe = pkgsrc / "devel/libstatgrab"

    with_perl = query(args.bmake, recipe, makeconf, sysroot, "yes")
    (work / "target-perl.log").write_text("\n".join(with_perl.values()) + "\n")
    if with_perl["PKG_FAIL_REASON"]:
        raise RuntimeError("Staged target Perl was rejected: " + with_perl["PKG_FAIL_REASON"])
    if "perl>=5.0" not in with_perl["DEPENDS"]:
        raise RuntimeError("Perl is not a target runtime dependency: " + with_perl["DEPENDS"])
    if with_perl["PERL5"] != "/usr/pkg/bin/perl":
        raise RuntimeError("Perl replacement uses a non-target path: " + with_perl["PERL5"])

    empty_sysroot = work / "empty-sysroot"
    empty_sysroot.mkdir()
    without_perl = query(args.bmake, recipe, makeconf, empty_sysroot, "yes")
    (work / "missing-target-perl.log").write_text(
        "\n".join(without_perl.values()) + "\n"
    )
    if "perl:run not supported in cross-compilation" not in without_perl["PKG_FAIL_REASON"]:
        raise RuntimeError("Missing target Perl was not refused: " + without_perl["PKG_FAIL_REASON"])

    native = query(args.bmake, recipe, makeconf, sysroot, "no")
    (work / "native.log").write_text("\n".join(native.values()) + "\n")
    if "not supported in cross-compilation" in native["PKG_FAIL_REASON"]:
        raise RuntimeError("Native Perl selection changed: " + native["PKG_FAIL_REASON"])

    print("PASS: staged Perl is a target runtime dependency; absent target Perl is refused")


if __name__ == "__main__":
    main()
