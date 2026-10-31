#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check that cross Cargo uses the host rust-bin and the target std as tools."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys


def main():
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: rust-cross-selection.py PKGSRC MAKECONF BMAKE NEW_WORK"
        )

    pkgsrc = Path(sys.argv[1]).resolve(strict=True)
    makeconf = Path(sys.argv[2]).resolve(strict=True)
    bmake = Path(sys.argv[3]).resolve(strict=True)
    work = Path(sys.argv[4]).absolute()
    cargo = pkgsrc / "graphics/libimagequant/Makefile"
    if not cargo.is_file():
        raise SystemExit(f"missing pkgsrc consumer: {cargo}")
    rust_bin = pkgsrc / "lang/rust-bin/Makefile"
    if not rust_bin.is_file():
        raise SystemExit(f"missing pkgsrc provider: {rust_bin}")
    librsvg = pkgsrc / "graphics/librsvg/Makefile"
    bindgen = pkgsrc / "devel/rust-bindgen/Makefile"
    if not bindgen.is_file():
        raise SystemExit(f"missing pkgsrc consumer: {bindgen}")
    if not librsvg.is_file():
        raise SystemExit(f"missing pkgsrc consumer: {librsvg}")
    if not (pkgsrc / "EMBERBSD-CROSS-MK.CONF").is_file():
        raise SystemExit("pkgsrc export lacks EMBERBSD-CROSS-MK.CONF")
    if work.exists():
        raise SystemExit(f"refusing existing work directory: {work}")
    work.mkdir(parents=True)

    assignment = re.compile(r"^\s*RUST_TYPE\s*(?:\?=|\+=|=)")
    config_lines = makeconf.read_text(encoding="utf-8").splitlines(keepends=True)
    filtered = [line for line in config_lines if not assignment.match(line)]
    test_makeconf = work / "cross.mk.conf"
    test_makeconf.write_text("".join(filtered), encoding="utf-8")

    env = os.environ.copy()
    env.pop("RUST_TYPE", None)
    env["MAKECONF"] = str(test_makeconf)
    result = {}

    def query(package, variable, query_env, label):
        completed = subprocess.run(
            [str(bmake), "-C", str(package.parent), "show-var",
             f"VARNAME={variable}"],
            check=False,
            capture_output=True,
            text=True,
            env=query_env,
        )
        key = label.replace(".", "-").replace("/", "-")
        (work / f"{key}.log").write_text(
            completed.stdout + completed.stderr, encoding="utf-8"
        )
        if completed.returncode != 0:
            raise SystemExit(
                f"bmake query failed for {label}: {completed.returncode}"
            )
        result[label] = completed.stdout.strip()

    for variable in (
        "RUST_TYPE",
        "EMBERBSD_CROSS_RUST_STD",
        "BUILDLINK_PKGSRCDIR.rust-bin",
        "BUILDLINK_PKGSRCDIR.rust",
        "TOOL_DEPENDS",
        "BUILD_DEPENDS",
        "DEPENDS",
    ):
        query(cargo, variable, env, variable)

    query(librsvg, "RUST_TYPE", env, "graphics/librsvg RUST_TYPE")
    query(rust_bin, "PKG_FAIL_REASON", env, "lang/rust-bin PKG_FAIL_REASON")
    query(bindgen, "DEPENDS", env, "devel/rust-bindgen DEPENDS")

    std = result["EMBERBSD_CROSS_RUST_STD"]
    tools = result["TOOL_DEPENDS"].split()
    target = (result["BUILD_DEPENDS"] + " " + result["DEPENDS"]).split()
    checks = {
        "native Cargo mode": result["RUST_TYPE"] == "native",
        "target std package": re.fullmatch(r"rust-std-(aarch64|x86_64)-netbsd", std) is not None,
        "no rust-bin buildlink": result["BUILDLINK_PKGSRCDIR.rust-bin"] == "",
        "no rust buildlink": result["BUILDLINK_PKGSRCDIR.rust"] == "",
        "host rust-bin tool": any(d.startswith("rust-bin>=") and d.endswith(":../../lang/rust-bin") for d in tools),
        "target std tool": f"{std}-[0-9]*:../../lang/{std}" in tools,
        "no target Rust compiler": not any(re.search(r":\.\./\.\./lang/rust(-bin)?$", d) for d in target),
        "librsvg native override": result["graphics/librsvg RUST_TYPE"] == "native",
        "rust-bin refused for the target": "build-host compiler" in result["lang/rust-bin PKG_FAIL_REASON"],
        "no Rust runtime for target bindgen": not any(re.search(r":\.\./\.\./lang/rust(-bin)?$", d) for d in result["devel/rust-bindgen DEPENDS"].split()),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        (work / "result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise SystemExit(f"unexpected Rust provider selection: {failed!r}")

    result["pkgsrc"] = str(pkgsrc)
    result["makeconf"] = str(makeconf)
    result["explicit_rust_type_assignments_removed"] = len(config_lines) - len(filtered)
    (work / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("PASS: cross Cargo uses the host rust-bin and target std; rust-bin is not built for the target")


if __name__ == "__main__":
    main()
