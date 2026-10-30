#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check perl:run cross recipes before the target Perl is staged.

lang/perl5 builds the target Perl from the config.sh stored for the platform.
A perl:run recipe depends on it, so a bulk fetch, which runs before any
package is installed, and the first parse of a build must accept the recipe
when no Perl is staged in the sysroot yet. Without a stored config.sh for the
platform (and outside capture mode) the recipe is still refused.
"""

import argparse
import os
from pathlib import Path
import subprocess


VARIABLES = ("PKG_FAIL_REASON", "DEPENDS", "PERL5", "TOOLS_PATH.perl", "PREFIX",
             "MACHINE_PLATFORM")
RECIPES = ("devel/automake", "devel/gtexinfo", "print/ghostscript-agpl",
           "graphics/gd", "parallel/mpi-ch", "databases/mariadb118-client")
REFUSAL = "USE_TOOLS+=perl:run not supported in cross-compilation"


def query(bmake, recipe, makeconf, sysroot, extra):
    argv = [bmake, "-C", str(recipe), "MAKECONF=" + str(makeconf),
            "EMBERBSD_CROSS_SYSROOT=" + str(sysroot)] + extra
    for variable in VARIABLES:
        argv.extend(("-v", variable))
    env = dict(os.environ, MAKECONF=str(makeconf))
    result = subprocess.run(argv, check=True, text=True, env=env,
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    values = result.stdout.splitlines()
    if len(values) != len(VARIABLES):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    return dict(zip(VARIABLES, values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True,
                        help="cross MAKECONF without EMBERBSD_PERL_CAPTURE_CONFIG")
    parser.add_argument("--sysroot", type=Path, required=True,
                        help="target sysroot without usr/pkg/bin/perl")
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--bmake", required=True)
    parser.add_argument("recipes", nargs="*", default=RECIPES)
    args = parser.parse_args()

    pkgsrc = args.pkgsrc.resolve(strict=True)
    makeconf = args.makeconf.resolve(strict=True)
    sysroot = args.sysroot.resolve(strict=True)
    work = args.work.resolve()
    if work.exists():
        parser.error("Work directory already exists")
    if (sysroot / "usr/pkg/bin/perl").exists():
        parser.error("The sysroot must not contain a staged target Perl")
    work.mkdir(parents=True)
    absent = work / "absent-config.sh"

    failures = []
    for path in args.recipes:
        recipe = pkgsrc / path
        name = path.replace("/", "_")
        stored = query(args.bmake, recipe, makeconf, sysroot, [])
        (work / (name + ".stored.log")).write_text("\n".join(stored.values()) + "\n")
        config = pkgsrc / "lang/perl5/files/config" / (stored["MACHINE_PLATFORM"] + ".sh")
        if not config.is_file():
            parser.error("No stored Perl config.sh for " + stored["MACHINE_PLATFORM"])
        target = stored["PREFIX"] + "/bin/perl"
        if REFUSAL in stored["PKG_FAIL_REASON"]:
            failures.append(path + ": refused before the target Perl is staged")
        if ":../../lang/perl5" not in stored["DEPENDS"]:
            failures.append(path + ": lang/perl5 is not a run dependency")
        if stored["PERL5"] != target:
            failures.append(path + ": installed scripts use " + stored["PERL5"])
        if stored["TOOLS_PATH.perl"] in ("", target):
            failures.append(path + ": build steps do not run a host Perl")

        missing = query(args.bmake, recipe, makeconf, sysroot,
                        ["EMBERBSD_PERL_STORED_CONFIG=" + str(absent)])
        (work / (name + ".no-config.log")).write_text("\n".join(missing.values()) + "\n")
        if REFUSAL not in missing["PKG_FAIL_REASON"]:
            failures.append(path + ": accepted without a stored Perl config.sh")

    if failures:
        for failure in failures:
            print("FAIL: " + failure)
        raise SystemExit(1)
    print("PASS: %d perl:run recipes accepted with the stored Perl config and "
          "no staged Perl; refused without a stored config" % len(args.recipes))


if __name__ == "__main__":
    main()
