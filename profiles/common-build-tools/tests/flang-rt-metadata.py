#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Run actual flang-rt pkgsrc metadata and missing-driver guards."""
import argparse
from pathlib import Path
import subprocess
import tempfile
p = argparse.ArgumentParser()
for name in ("bmake", "pkgsrc", "makeconf"):
    p.add_argument("--" + name, type=Path, required=True)
a = p.parse_args()
assert all(x.is_absolute() for x in vars(a).values())
tmp = tempfile.TemporaryDirectory(prefix="flang-rt-missing-")
missing = str(Path(tmp.name) / "absent-flang")
def query(*goals):
    return subprocess.run([str(a.bmake), "-C", str(a.pkgsrc / "lang/flang-rt"),
        "MAKECONF=" + str(a.makeconf), "EMBERBSD_FLANG=" + missing, "USE_CROSS_COMPILE=yes", "_MAKEVARS_MK=defined",
        *goals, "-V", "${PKGNAME}", "-V", "${PKG_FAIL_REASON}"],
        text=True, capture_output=True, timeout=120, check=True)
for goal in ("show-var", "show-vars"):
    r = query(goal)
    assert r.stdout.splitlines()[0].startswith("flang-rt-") and not r.stdout.splitlines()[1], r.stdout
    assert not r.stderr, r.stderr
for goals in ((), ("all",), ("all", "show-vars")):
    r = query(*goals)
    assert "EMBERBSD_FLANG must select the build-host Ports flang driver" in r.stdout, r.stdout
print("PASS: actual flang-rt metadata and build guard")
