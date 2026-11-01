#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Exercise pkgsrc's real Perl PLIST expansion.
"""Check Perl's conditional native helper entries in target and native PLISTs.

Use pkgsrc's plist.mk and selected SDK bmake/utility programs. No package is
built or installed; both cases expand the actual lang/perl5/PLIST.
"""
import argparse
import os
from pathlib import Path
import subprocess


def require(value, message):
    if not value:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bmake", "pkgsrc", "sdk_bin", "gnu_bin", "shell", "work"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    args = parser.parse_args()
    require(args.pkgsrc.is_absolute() and (args.pkgsrc / "mk/plist/plist.mk").is_file(),
            "Select an actual pkgsrc tree with mk/plist/plist.mk")
    for path in (args.bmake, args.shell, args.sdk_bin / "nawk"):
        require(path.is_absolute() and path.is_file() and os.access(path, os.X_OK),
                "Select executable absolute SDK tools")
    gnu_tools = {name: args.gnu_bin / name for name in ("cat", "env", "mkdir", "rm", "test", "true")}
    require(all(path.is_file() and os.access(path, os.X_OK) for path in gnu_tools.values()),
            "Selected native utility prefix lacks required pkgsrc PLIST tools")
    work = args.work
    require(work.is_absolute() and work.resolve() == work and not os.path.lexists(work),
            "Use a fresh absolute output directory")
    work.mkdir(mode=0o700)
    pkgsrc_view = work / "pkgsrc"
    package_dir = pkgsrc_view / "lang/perl5"
    package_dir.mkdir(parents=True)
    (pkgsrc_view / "mk").symlink_to(args.pkgsrc / "mk", target_is_directory=True)

    repo = Path(__file__).resolve().parents[3]
    recipe = repo / "pkgsrc/lang/perl5"
    makefile = package_dir / "Makefile"
    lines = [
        "OPSYS= NetBSD", "OS_VERSION= 11.0", "MACHINE_ARCH= aarch64",
        "MACHINE_GNU_ARCH= aarch64", "MACHINE_GNU_PLATFORM= aarch64-unknown-netbsd",
        "LOWER_VENDOR= unknown", "LOWER_OPSYS= netbsd", "PREFIX= /usr/pkg",
        "LOCALBASE= /usr/pkg", "PKGSRCDIR= " + str(args.pkgsrc),
        "PKGDIR= " + str(recipe), "PLIST_SRC= ${PKGDIR}/PLIST",
        "PKGVERSION_NOREV= 5.44.0", "PKGVERSION= 5.44.0nb13",
        "PKGNAME_NOREV= perl-5.44.0", "PKGBASE= perl", "PKGMANDIR= man",
        "SHLIB_TYPE= ELF", "SHLIB_EXT= .so", "DESTDIR=", "RUN=",
        "AWK= " + str(args.sdk_bin / "nawk"),
        "PKGSRC_SETENV= " + str(gnu_tools["env"]),
        "TOOLS_TEST= " + str(gnu_tools["test"]),
        "TEST= " + str(gnu_tools["test"]),
        "MKDIR= " + str(gnu_tools["mkdir"]),
        "CAT= " + str(gnu_tools["cat"]),
        "RM= " + str(gnu_tools["rm"]),
        "TRUE= " + str(gnu_tools["true"]),
        '.include "' + str(recipe / "host-tools.mk") + '"',
        '.include "' + str(args.pkgsrc / "mk/plist/plist.mk") + '"',
        "",
    ]
    makefile.write_text("\n".join(lines))
    env = dict(os.environ)
    env.update(PATH=str(args.sdk_bin) + os.pathsep + str(args.gnu_bin),
               SHELL=str(args.shell), LC_ALL="C", TZ="UTC", TMPDIR=str(work))

    helper_names = ("generate_uudmap", "miniperl")
    outputs = {}
    for role, cross in (("target", "yes"), ("native", "no")):
        plist = work / f"{role}.plist"
        result = subprocess.run(
            [str(args.bmake), "-f", str(makefile), f"USE_CROSS_COMPILE={cross}",
             f"PLIST={plist}", "plist"], cwd=package_dir, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        require(result.returncode == 0,
                f"{role} PLIST expansion failed ({result.returncode}):\n{result.stdout}\n{result.stderr}")
        expanded = plist.read_text()
        active = Path(str(plist) + "_nokeywords").read_text()
        active_lines = active.splitlines()
        require("${PLIST.hosttools}" not in expanded,
                f"{role} PLIST retained a literal PLIST.hosttools token")
        if role == "target":
            commented = [line for line in expanded.splitlines()
                         if line.startswith("@comment libexec/perl5/")]
            require(all(any(line.endswith(name) for line in commented)
                        for name in helper_names),
                    "Target PLIST did not comment both native helper entries")
            require(not any("libexec/perl5/" in line for line in active_lines),
                    "Target package PLIST contains native helper entries")
        else:
            require(all(any("libexec/perl5/" in line and line.endswith(name)
                            for line in active_lines) for name in helper_names),
                    "Native package PLIST lost one of its installed helpers")
        outputs[role] = {"active_helpers": [line for line in active_lines
                                            if "libexec/perl5/" in line]}
    print("PASS: " + str(outputs))


if __name__ == "__main__":
    main()
