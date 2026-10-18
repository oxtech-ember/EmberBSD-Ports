#!/usr/bin/env python3
"""Check the production Sxmo clock-selection fix on a native host."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

archive, work = map(Path, sys.argv[1:])
assert not work.exists(), "Work directory must be new"
assert hashlib.sha256(archive.read_bytes()).hexdigest() == "65de6470f7331b86b90c4644f13074c3edaff6fdb98a2f43b3f53750a924d8d4"
work.mkdir(parents=True)
here = Path(__file__).resolve().parent
with tarfile.open(archive) as source:
    source.extractall(work, filter="data")
tree = work / "sxmo-utils-1.18.1"
include = work / "include/sys"
include.mkdir(parents=True)
shutil.copyfile(here / "timerfd-fixture.h", include / "timerfd.h")
cc = os.environ.get("CC", "/usr/bin/cc")
flags = ["-std=c99", "-D_POSIX_C_SOURCE=200809L", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined", "-I" + str(include.parent), "-I" + str(here)]
command = [cc, *flags, str(tree / "programs/sxmo_sleep.c"), str(here / "timerfd-fixture.c"), "-o", str(work / "sleep")]
baseline = subprocess.run(command, capture_output=True, text=True)
(work / "baseline-compile.log").write_text(baseline.stdout + baseline.stderr)
assert baseline.returncode != 0 and "CLOCK_BOOTTIME" in baseline.stderr
subprocess.run(["patch", "-p0", "-F", "0", "-i", str(here.parent / "patches/patch-programs_sxmo_sleep.c")], cwd=tree, check=True)
subprocess.run(command, check=True)
# Native values come from an independent tiny clock-header query.
query = work / "clock-values.c"
query.write_text('#include <time.h>\n#include <stdio.h>\nint main(void) { printf("%d %d", (int)CLOCK_REALTIME, (int)CLOCK_MONOTONIC); }\n')
subprocess.run([cc, "-D_POSIX_C_SOURCE=200809L", str(query), "-o", str(work / "clock-values")], check=True)
realtime, monotonic = subprocess.check_output([str(work / "clock-values")], text=True).split()
cases = [([], 1, "duration", realtime), (["3"], 0, "", realtime), (["-c", "monotonic", "3"], 0, "", monotonic), (["-c", "realtime", "3"], 0, "", realtime), (["-c", "boottime", "3"], 1, "not supported", realtime), (["-c", "realtime_alarm", "3"], 1, "not supported", realtime), (["-c", "boottime_alarm", "3"], 1, "not supported", realtime), (["-c", "unknown", "3"], 1, "Unknown clock", realtime)]
for number, (arguments, status, diagnostic, clock) in enumerate(cases):
    result = subprocess.run([str(work / "sleep"), *arguments], env={**os.environ, "SXMO_TEST_CLOCK": clock}, capture_output=True, text=True)
    assert (result.returncode, result.stdout) == (status, ""), (arguments, result)
    assert diagnostic in result.stderr, (arguments, result.stderr)
    (work / f"case-{number}.log").write_text(result.stderr)
# Removing one guard must reproduce the target-independent compile failure.
production = tree / "programs/sxmo_sleep.c"
original = production.read_text()
production.write_text(original.replace("#ifdef CLOCK_BOOTTIME\n", "#if 1\n", 1))
assert subprocess.run(command, capture_output=True).returncode != 0
production.write_text(original)
subprocess.run(command, check=True)
print(f"PASS: {len(cases)} production CLI cases; original and mutation compile controls; ASan/UBSan")
