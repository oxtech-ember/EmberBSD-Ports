#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the CMake Zstandard archive API used by Qt Core."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--cmake", required=True)
parser.add_argument("--work", required=True)
args = parser.parse_args()
cmake = Path(args.cmake)
work = Path(args.work)
if not cmake.is_absolute() or not cmake.is_file() or not work.is_absolute():
    parser.error("Use an existing absolute CMake executable and a new absolute work path")
work.mkdir()
payload = b"Qt MIME archive API regression\n" * 128
(work / "fixture").write_bytes(payload)

def run(arguments, directory):
    result = subprocess.run([str(cmake), "-E", *arguments], cwd=directory,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        raise SystemExit("FAIL: CMake archive API: " + result.stdout[-2048:])

run(["tar", "cf", "fixture.tar.zst", "--zstd", "fixture"], work)
archive = work / "fixture.tar.zst"
if archive.read_bytes()[:4] != bytes.fromhex("28b52ffd"):
    raise SystemExit("FAIL: CMake did not produce a Zstandard frame")
output = work / "extracted"
output.mkdir()
run(["tar", "xf", str(archive)], output)
if (output / "fixture").read_bytes() != payload:
    raise SystemExit("FAIL: archive roundtrip changed the input")
print("PASS: CMake Zstandard create, frame, and extract roundtrip")
