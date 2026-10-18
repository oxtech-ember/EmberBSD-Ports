#!/usr/bin/env python3
"""Run real NetBSD timerfd helpers on an explicitly selected SSH target."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid

host, build_arg, logs_arg = sys.argv[1:]
build, logs = Path(build_arg), Path(logs_arg)
assert not logs.exists(), "Use a new result directory"
receipt = json.loads((build / "receipt.json").read_text())
names = ("sxmo_sleep", "sxmo_aligned_sleep")
for name in names:
    assert receipt["helpers"][name]["status"] == 0
    assert hashlib.sha256((build / name).read_bytes()).hexdigest() == receipt["helpers"][name]["sha256"]
logs.mkdir(parents=True)
remote = "/tmp/emberbsd-sxmo-timers-" + uuid.uuid4().hex

def ssh(command, data=None):
    return subprocess.run(["ssh", host, command], input=data, capture_output=True, timeout=30)

identity = ssh("uname -srm")
assert identity.returncode == 0 and identity.stdout.startswith(b"NetBSD ")
(logs / "target.txt").write_bytes(identity.stdout + identity.stderr)
result = ssh("umask 077; mkdir " + shlex.quote(remote))
assert result.returncode == 0, result.stderr
try:
    for name in names:
        result = ssh("cat > " + shlex.quote(remote + "/" + name) + "; chmod 700 " + shlex.quote(remote + "/" + name), (build / name).read_bytes())
        assert result.returncode == 0, result.stderr
    cases = [
        ("sxmo_sleep", ["1"], 0, b"", True),
        ("sxmo_sleep", ["-c", "realtime", "1"], 0, b"", True),
        ("sxmo_sleep", ["-c", "monotonic", "1"], 0, b"", True),
        ("sxmo_sleep", ["-c", "boottime", "1"], 1, b"not supported", False),
        ("sxmo_sleep", ["-c", "realtime_alarm", "1"], 1, b"not supported", False),
        ("sxmo_sleep", ["-c", "boottime_alarm", "1"], 1, b"not supported", False),
        ("sxmo_sleep", ["0"], 1, b"duration", False),
        ("sxmo_aligned_sleep", ["1"], 0, b"", False),
    ]
    for number, (name, arguments, status, diagnostic, measure) in enumerate(cases):
        command = shlex.join([remote + "/" + name, *arguments])
        if measure:
            command = "/usr/bin/time -p " + command
        result = ssh(command)
        (logs / f"case-{number}.stdout").write_bytes(result.stdout)
        (logs / f"case-{number}.stderr").write_bytes(result.stderr)
        (logs / f"case-{number}.status").write_text(str(result.returncode) + "\n")
        assert result.returncode == status, (arguments, result)
        assert result.stdout == b"" and diagnostic in result.stderr, result
        if measure:
            match = re.search(rb"(?:^|\n)real\s+([0-9.]+)", result.stderr)
            assert match and 0.8 <= float(match.group(1)) <= 10.0, result.stderr
    (logs / "receipt.json").write_text(json.dumps({"source_sha256": receipt["source_sha256"], "payload": {name: receipt["helpers"][name]["sha256"] for name in names}, "executed": len(cases), "failed": 0}, indent=2) + "\n")
    print(f"PASS: {len(cases)} real target timerfd CLI cases, including three timed one-second waits")
finally:
    cleanup = ssh("rm -rf " + shlex.quote(remote))
    assert cleanup.returncode == 0, cleanup.stderr
