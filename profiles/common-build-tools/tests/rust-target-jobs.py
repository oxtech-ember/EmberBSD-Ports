#!/usr/bin/env python3
"""Check that both std bootstrap invocations obey the resource limit."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import json
import os
from pathlib import Path
import subprocess
import sys

work = Path(sys.argv[1]).resolve()
assert not work.exists(), "Use a new work directory"
for directory in ("source", "work", "host", "tools/bin", "sysroot"):
    (work / directory).mkdir(parents=True)
(work / "tools/bin/aarch64--netbsd-gcc").write_text("# Never executed by this build-command test\n")
(work / "source/x.py").write_text('''import json, sys
from pathlib import Path
with Path("calls.jsonl").open("a") as out:
    out.write(json.dumps(sys.argv[1:]) + "\\n")
print("Building stage0 library artifacts")
''')
helper = Path(__file__).resolve().parents[1] / "../../pkgsrc/lang/rust-std-aarch64-netbsd/files/target-std.sh"
command = ["sh", str(helper), "build", *map(str, [work / item for item in
           ("source", "work", "host", "tools", "sysroot")]), sys.executable]
for jobs in ("1", "3"):
    calls = work / "source/calls.jsonl"
    calls.unlink(missing_ok=True)
    result = subprocess.run(command, env={**os.environ, "EMBERBSD_RUST_BUILD_JOBS": jobs}, capture_output=True)
    assert result.returncode == 0, result.stderr
    invocations = [json.loads(line) for line in calls.read_text().splitlines()]
    assert len(invocations) == 2 and all("-j" + jobs in args for args in invocations), invocations
    assert "--dry-run" in invocations[0] and "--dry-run" not in invocations[1]
for jobs in ("", "0", "-1", "2;echo", "1.5"):
    calls.unlink(missing_ok=True)
    result = subprocess.run(command, env={**os.environ, "EMBERBSD_RUST_BUILD_JOBS": jobs}, capture_output=True)
    assert result.returncode == 2 and not calls.exists(), jobs
print("PASS: both bootstrap stages obey jobs=1 and3; five invalid counts fail before execution")
