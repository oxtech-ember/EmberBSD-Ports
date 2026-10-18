#!/usr/bin/env python3
"""Cross-build the real Sxmo helpers and preserve every exit status."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument("archive", type=Path)
parser.add_argument("cc", type=Path)
parser.add_argument("sysroot", type=Path)
parser.add_argument("work", type=Path)
args = parser.parse_args()
assert all(p.is_absolute() for p in (args.archive, args.cc, args.sysroot, args.work))
assert not args.work.exists(), "Use a new work directory"
assert hashlib.sha256(args.archive.read_bytes()).hexdigest() == "65de6470f7331b86b90c4644f13074c3edaff6fdb98a2f43b3f53750a924d8d4"
version = subprocess.check_output([str(args.cc), "--version"], text=True)
assert "16.2.0" in version.splitlines()[0]
triplet = subprocess.check_output([str(args.cc), "-dumpmachine"], text=True).strip()
assert triplet == "aarch64--netbsd", triplet
args.work.mkdir(parents=True)
with tarfile.open(args.archive) as archive:
    archive.extractall(args.work, filter="data")
source = args.work / "sxmo-utils-1.18.1"
here = Path(__file__).resolve().parent
for patch in sorted((here / "patches").glob("patch-*")):
    subprocess.run(["patch", "-p0", "-F", "0", "-i", str(patch)], cwd=source, check=True)
runtime = args.sysroot / "usr/pkg/gcc16"
cflags = ["-Wall", "-std=c99", "-D_POSIX_C_SOURCE=200809L", "--sysroot=" + str(args.sysroot), "-I" + str(args.sysroot / "usr/pkg/include")]
ldflags = ["--sysroot=" + str(args.sysroot), "-B" + str(runtime / "lib/gcc/aarch64--netbsd/16.2.0") + "/", "-L" + str(runtime / "lib"), "-Wl,-rpath,/usr/pkg/gcc16/lib"]
receipt = {"source_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(), "compiler": version.splitlines()[0], "triplet": triplet, "helpers": {}}
for name in ("sxmo_aligned_sleep", "sxmo_sleep", "sxmo_status_led", "sxmo_vibrate"):
    command = [str(args.cc), *cflags, str(source / "programs" / (name + ".c")), *ldflags, "-o", str(args.work / name)]
    if name == "sxmo_status_led":
        command.append("-lm")
    run = subprocess.run(command, capture_output=True, text=True)
    (args.work / (name + ".log")).write_text(run.stdout + run.stderr)
    result = {"command": command, "status": run.returncode}
    if run.returncode == 0:
        result["sha256"] = hashlib.sha256((args.work / name).read_bytes()).hexdigest()
    receipt["helpers"][name] = result
    print(f"{name}: compiler status {run.returncode}", flush=True)
(args.work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
raise SystemExit(any(value["status"] != 0 for value in receipt["helpers"].values()))
