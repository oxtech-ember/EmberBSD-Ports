#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Run focused Bosch BMM150 API transport-error regressions."""

import argparse
import pathlib
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--cc", required=True)
parser.add_argument("--source-dir", required=True, type=pathlib.Path)
parser.add_argument("--out-dir", required=True)
args = parser.parse_args()

source_dir = args.source_dir.resolve()
test_source = pathlib.Path(__file__).with_suffix(".c")
out_dir = pathlib.Path(args.out_dir).resolve()
out_dir.mkdir(parents=True, exist_ok=True)
binary = out_dir / "t_bmm150_api"

subprocess.run(
    [
        args.cc,
        "-std=c11",
        "-O1",
        "-g",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-fsanitize=address,undefined",
        "-fno-sanitize-recover=all",
        "-I",
        str(source_dir),
        str(test_source),
        str(source_dir / "bmm150.c"),
        "-o",
        str(binary),
    ],
    check=True,
)
subprocess.run([str(binary)], check=True)
print("BMM150 API transport-error propagation passed")
