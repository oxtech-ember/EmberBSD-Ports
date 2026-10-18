#!/usr/bin/env python3
"""Run the upstream luit controls and exact-byte conversion regressions."""

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", help="absolute native or target luit path")
    parser.add_argument("output", type=Path)
    parser.add_argument("--ssh", help="explicit target host for execution")
    parser.add_argument("--ssh-program", default="ssh")
    args = parser.parse_args()
    if not args.binary.startswith("/"):
        parser.error("binary must be an absolute path")
    if args.output.exists():
        parser.error("output directory already exists")
    args.output.mkdir(parents=True)
    cases = [([option], None, None) for option in (
        "-V", "-h", "-list", "-list-builtin", "-list-fontenc", "-list-iconv")]
    cases += [(["-c", "-encoding", "ISO8859-1"], b"caf\xe9\n", "café\n".encode()),
              (["-c", "-encoding", "UTF-8"], "Привет\n".encode(), "Привет\n".encode())]
    environment = dict(os.environ, LC_ALL="C", ASAN_OPTIONS="halt_on_error=1",
                       UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    results = []
    for index, (options, data, expected) in enumerate(cases):
        command = [args.binary] + options
        if args.ssh:
            command = [args.ssh_program, args.ssh,
                       "env LC_ALL=C " + shlex.join(command)]
        result = subprocess.run(command, input=data, capture_output=True,
                                timeout=30, env=environment)
        (args.output / f"{index:02}.stdout").write_bytes(result.stdout)
        (args.output / f"{index:02}.stderr").write_bytes(result.stderr)
        matched = expected is None or result.stdout == expected
        sanitizer = b"AddressSanitizer" in result.stderr or b"runtime error:" in result.stderr
        results.append({"command": command, "status": result.returncode,
                        "expected_bytes_match": matched, "sanitizer_diagnostic": sanitizer,
                        "passed": result.returncode == 0 and matched and not sanitizer})
    (args.output / "result.json").write_text(json.dumps(results, indent=2) + "\n")
    failed = sum(not result["passed"] for result in results)
    if failed:
        raise SystemExit(f"FAIL: {failed} luit checks; inspect {args.output}")
    print("PASS: six upstream controls and two exact-byte encoding conversions")


if __name__ == "__main__":
    main()
