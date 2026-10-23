#!/usr/bin/env python3
"""Run the actual BSD name provider with host ASan and UBSan."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, required=True,
                    help="Clean libevdev-openbsd source at the recorded commit")
parser.add_argument("--input-headers", type=Path, required=True,
                    help="Installed input-headers include directory")
parser.add_argument("--work", type=Path, required=True)
args = parser.parse_args()
assert not args.work.exists(), "Use a new work directory"
args.work.mkdir(parents=True)
tree = args.work / "source"
shutil.copytree(args.source, tree)
# Darwin needs the same BSD code definitions that the target header selects.
# Route the original headers. Do not copy numeric constants or ioctl values.
include = args.work / "include/linux"
include.mkdir(parents=True)
for name in ("input.h", "input-event-codes.h"):
    (include / name).symlink_to((args.input_headers / "linux/freebsd" / name).resolve())
cc = os.environ.get("CC", "/usr/bin/cc")
test = Path(__file__).with_name("input-names.c").resolve()
executable = args.work / "input-names"
command = [cc, "-std=c99", "-O1", "-g", "-include", "stdint.h",
           "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
           "-I" + str(include.parent), "-I" + str(tree),
           str(test), str(tree / "libevdev.c"), "-o", str(executable)]
leaks = sys.platform != "darwin"
environment = {**os.environ, "ASAN_OPTIONS": f"detect_leaks={int(leaks)}:halt_on_error=1",
               "UBSAN_OPTIONS": "halt_on_error=1"}
baseline = subprocess.run(command, capture_output=True)
(args.work / "baseline.stderr").write_bytes(baseline.stderr)
assert baseline.returncode != 0, "The original source lacks the added name APIs"
patches = Path(__file__).resolve().parents[3] / "pkgsrc/devel/libevdev-chunk/patches"
for patch in sorted(patches.glob("patch-*")):
    subprocess.run(["patch", "-p0", "-F", "0", "-i", str(patch)], cwd=tree, check=True)
subprocess.run(command, check=True)
subprocess.run([str(executable)], env=environment, check=True)
# Prove that a wrong event code is detected independently of its name table.
production = tree / "libevdev.c"
original = production.read_text()
needle = "return entry ? (int)entry->value : -1;"
assert original.count(needle) == 3
production.write_text(original.replace(needle, "return entry ? (int)entry->value + 1 : -1;", 1))
subprocess.run(command, check=True)
negative = subprocess.run([str(executable)], env=environment, capture_output=True)
(args.work / "negative.stderr").write_bytes(negative.stderr)
assert negative.returncode != 0
production.write_text(original)
subprocess.run(command, check=True)
receipt = {"command": command, "compiler": subprocess.check_output([cc, "--version"], text=True),
           "contracts": 14, "baseline_missing_api": True, "wrong_code_control": True,
           "sanitizers": ["address", "undefined"],
           "leak_sanitizer_supported": leaks,
           "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest()}
(args.work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("PASS: 14 production API contracts with ASan/UBSan; original API and wrong-code controls")
