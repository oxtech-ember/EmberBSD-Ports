#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check that cross pkgsrc selects the shared build-host Rust provider."""

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
    cargo_c = pkgsrc / "devel/cargo-c/Makefile"
    if not cargo_c.is_file():
        raise SystemExit(f"missing pkgsrc consumer: {cargo_c}")
    librsvg = pkgsrc / "graphics/librsvg/Makefile"
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
        "BUILDLINK_PKGSRCDIR.rust-bin",
        "BUILDLINK_PKGSRCDIR.rust",
    ):
        query(cargo_c, variable, env, variable)

    query(librsvg, "RUST_TYPE", env, "graphics/librsvg RUST_TYPE")

    expected = {
        "RUST_TYPE": "bin",
        "BUILDLINK_PKGSRCDIR.rust-bin": "../../lang/rust-bin",
        "BUILDLINK_PKGSRCDIR.rust": "",
        "graphics/librsvg RUST_TYPE": "native",
    }
    if result != expected:
        (work / "result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise SystemExit(f"unexpected Rust provider selection: {result!r}")

    result["pkgsrc"] = str(pkgsrc)
    result["makeconf"] = str(makeconf)
    result["explicit_rust_type_assignments_removed"] = len(config_lines) - len(filtered)
    (work / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("PASS: cross Cargo selects rust-bin and librsvg keeps its native override")


if __name__ == "__main__":
    main()
