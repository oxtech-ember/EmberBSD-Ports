#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual pkgsrc bootstrap dependency metadata.
"""Check shared zlib selection for bootstrap consumers and compiler roles."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pkgsrc", "native_makeconf", "cross_makeconf", "new_work"):
        parser.add_argument(name)
    parser.add_argument("--native-only", action="store_true", help="Skip cross compiler routing checks.")
    args = parser.parse_args()
    tree = Path(args.pkgsrc).resolve(strict=True)
    configs = {name: Path(getattr(args, name + "_makeconf")).resolve(strict=True)
               for name in ("native", "cross")}
    out = Path(args.new_work).absolute()
    require(not out.exists() and not out.is_symlink(), "Output exists.")
    out.mkdir(parents=True)
    for kind, path in configs.items():
        config = out / (kind + ".conf")
        config.write_text(re.sub(r"^EMBERBSD_BSDTAR_USE_COMMON_ZLIB\s*[?:+]?=.*\n", "",
                                 path.read_text(), flags=re.M))
        configs[kind] = config
    keys = ("PKGNAME DEPENDS CPPFLAGS LDFLAGS WRKDIR CC CXX USE_CROSS_COMPILE "
            "USE_BUILTIN.zlib").split()
    commands = []

    def query(name, config, extra, recipe="archivers/bsdtar"):
        argv = [os.environ.get("BMAKE", "bmake"), "-C", str(tree / recipe),
                "MAKECONF=" + str(configs[config]), "WRKOBJDIR=" + str(out / "objects"),
                "PACKAGES=" + str(out / "packages"), "_PKGSRC_BARRIER=yes", *extra]
        for key in keys:
            argv.extend(["-V", "${" + key + "}"])
        result = subprocess.run(argv, env=dict(os.environ, LC_ALL="C"),
                                capture_output=True, timeout=120)
        (out / (name + ".stdout")).write_bytes(result.stdout)
        (out / (name + ".stderr")).write_bytes(result.stderr)
        commands.append(dict(name=name, argv=argv, status=result.returncode))
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(result.returncode == 0, "Metadata query failed: " + name)
        lines = result.stdout.decode().splitlines()
        require(len(lines) == len(keys), "Unexpected metadata shape.")
        return dict(zip(keys, lines))

    results = {"bootstrap": query("bootstrap", "native", ["EMBERBSD_BSDTAR_USE_COMMON_ZLIB=no"])}
    before = results["bootstrap"]
    require(before["PKGNAME"] == "bsdtar-3.8.11" and "zlib>=1.3.2nb1" in before["DEPENDS"],
            "Default bootstrap must use the registered current zlib package.")
    require(before["USE_BUILTIN.zlib"] == "no", "Bootstrap selected host zlib.")
    require(not any(before["WRKDIR"] + "/zlib" in before[key]
                    for key in ("CPPFLAGS", "LDFLAGS")), "Embedded zlib source flags remain.")
    for name, (config, extra) in {
        "native-opt-in": ("native", ["EMBERBSD_BSDTAR_USE_COMMON_ZLIB=yes"]),
        "native-common": ("native", ["EMBERBSD_COMMON_TOOLS=yes"]),
        "target": ("cross", []),
        "host-recursion": ("cross", ["USE_CROSS_COMPILE=no"]),
    }.items():
        if args.native_only and config == "cross":
            continue
        row = query(name, config, extra)
        require(row["PKGNAME"] == "bsdtar-3.8.11" and "zlib>=1.3.2nb1" in row["DEPENDS"]
                and row["USE_BUILTIN.zlib"] == "no", "Current zlib package was not selected: " + name)
        require(not any(row["WRKDIR"] + "/zlib" in row[key] for key in ("CPPFLAGS", "LDFLAGS")),
                "Copied-source flags remain: " + name)
        results[name] = row
    require(all(results["native-opt-in"][key] == before[key] for key in ("CC", "CXX", "USE_CROSS_COMPILE")),
            "Native compiler routing changed.")
    require(results["native-common"] == results["native-opt-in"], "Common default differs from explicit opt-in.")
    if not args.native_only:
        require(results["target"]["USE_CROSS_COMPILE"].lower() == "yes" and
                "aarch64--netbsd-gcc" in results["target"]["CC"], "Target compiler was lost.")
        require(results["host-recursion"]["USE_CROSS_COMPILE"].lower() == "no" and
                "aarch64--netbsd-" not in results["host-recursion"]["CC"], "Host tool was forced cross.")
    for name, extra in (("pkg-install-default", []), ("pkg-install-prefer-host", ["PREFER_PKGSRC=no"])):
        row = query(name, "native", extra, "pkgtools/pkg_install")
        require(row["PKGNAME"].endswith("nb5") and "zlib>=1.3.2nb1" in row["DEPENDS"]
                and row["USE_BUILTIN.zlib"] == "no", "pkg_install lost shared zlib: " + name)
        require(not any(row["WRKDIR"] + "/zlib" in row[key] for key in ("CPPFLAGS", "LDFLAGS")),
                "pkg_install kept embedded zlib flags.")
        results[name] = row
    for recipe in ("archivers/bsdtar", "pkgtools/pkg_install"):
        source = (tree / recipe / "Makefile").read_text()
        require('FILESDIR.zlib' not in source and '${WRKDIR}/zlib' not in source,
                "Recipe still requires absent embedded zlib sources: " + recipe)
        require('--without-zlib' not in source, "Recipe disables zlib: " + recipe)
    (out / "result.json").write_text(json.dumps(dict(
        scope="Actual pkgsrc dependency and compiler metadata; no build or target execution.",
        cross_checked=not args.native_only, results=results), indent=2) + "\n")
    print("PASS: current registered-package dependency, default bootstrap, pkg_install and native compiler identity.")
    print("SKIP: cross compiler routing." if args.native_only else "PASS: cross compiler routing and host recursion.")


if __name__ == "__main__":
    main()
