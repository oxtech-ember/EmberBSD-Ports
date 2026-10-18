#!/usr/bin/env python3
"""Execute unchanged JSON-C tests against its installed target library."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--host", required=True, help="Explicit SSH target")
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--build", type=Path, required=True)
parser.add_argument("--results", type=Path, required=True)
args = parser.parse_args()
assert not args.results.exists(), "Use a new result directory"
args.results.mkdir(parents=True)
remote = "/tmp/emberbsd-json-tests-" + uuid.uuid4().hex
payload = {}
buffer = io.BytesIO()
with tarfile.open(fileobj=buffer, mode="w") as archive:
    archive.add(args.source / "tests", "source/tests")
    for folder in ("tests", "apps"):
        for path in sorted((args.build / folder).iterdir()):
            if path.is_file() and path.read_bytes()[:4] == b"\x7fELF":
                archive.add(path, "build/" + folder + "/" + path.name)
                payload[folder + "/" + path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
tests = sorted(path.stem for path in (args.source / "tests").glob("*.test")
               if "tests/" + path.stem in payload or path.stem == "test_json_parse_cli")
assert len(tests) == 28, tests

def ssh(command, data=None):
    return subprocess.run(["ssh", "-o", "ConnectTimeout=15", args.host, command],
                          input=data, capture_output=True, timeout=120)

identity = ssh("uname -srm; /usr/sbin/pkg_info -e json-c")
assert identity.returncode == 0 and identity.stdout.startswith(b"NetBSD "), identity.stderr
(args.results / "target.txt").write_bytes(identity.stdout + identity.stderr)
result = ssh("umask 077; mkdir " + shlex.quote(remote))
assert result.returncode == 0, result.stderr
statuses = {}
try:
    result = ssh("cd " + shlex.quote(remote) + " && tar xf -", buffer.getvalue())
    assert result.returncode == 0, result.stderr
    for test in tests:
        command = ("cd " + shlex.quote(remote) + " && " + shlex.join([
            "env", "USE_VALGRIND=0", "VERBOSE=1", "LD_LIBRARY_PATH=/usr/pkg/lib",
            "srcdir=" + remote + "/source/tests", "top_builddir=" + remote + "/build",
            "sh", remote + "/source/tests/" + test + ".test"]))
        result = ssh(command)
        (args.results / (test + ".stdout")).write_bytes(result.stdout)
        (args.results / (test + ".stderr")).write_bytes(result.stderr)
        statuses[test] = result.returncode
    (args.results / "receipt.json").write_text(json.dumps({"payload": payload,
        "test_sha256": {name: hashlib.sha256((args.source / "tests" / (name + ".test")).read_bytes()).hexdigest() for name in tests},
        "statuses": statuses, "memory_checker": "none; separate host ASan/UBSan run"}, indent=2) + "\n")
    assert all(status == 0 for status in statuses.values()), statuses
    print(f"PASS: {len(tests)} upstream JSON-C target test scripts and independent expected outputs")
finally:
    result = ssh("rm -rf " + shlex.quote(remote) + "; test ! -e " + shlex.quote(remote))
    assert result.returncode == 0, result.stderr
