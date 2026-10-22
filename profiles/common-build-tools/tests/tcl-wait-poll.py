#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compare actual Tcl Unix wait functions.

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

CASES = ("indefinite-eintr", "negative-eintr", "zero-empty", "zero-ready",
         "read-ready", "write-ready", "exception-ready", "finite-eintr-expiry",
         "large-safe", "large-overflow", "int-max")


def function(path):
    source = path.read_text()
    start = source.index("\nint\nTclUnixWaitForFile(") + 1
    end = source.index("\n}\n#endif", start) + 3
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("generic_headers", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cc", type=Path, required=True)
    parser.add_argument("--cflag", action="append", default=[])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    records = []

    def run(command):
        result = subprocess.run([str(x) for x in command], text=True,
                                capture_output=True, timeout=30)
        records.append({"argv": [str(x) for x in command],
                        "returncode": result.returncode,
                        "stdout": result.stdout, "stderr": result.stderr})
        return result

    fixture = Path(__file__).with_suffix(".c")
    for variant, source, flags in (
        ("before-zero", args.before, ["-O0", "-ftrivial-auto-var-init=zero"]),
        ("after-zero", args.after, ["-O0", "-ftrivial-auto-var-init=zero"]),
        ("after-normal", args.after, ["-O2"]),
        ("before-ubsan", args.before, ["-O1", "-fsanitize=undefined",
                                      "-fno-sanitize-recover=all"]),
        ("after-sanitizers", args.after, ["-O1", "-fsanitize=address,undefined",
                                         "-fno-sanitize-recover=all"]),
    ):
        directory = args.output / variant
        directory.mkdir()
        (directory / "tcl-wait-function.inc").write_text(function(source))
        program = directory / "wait-poll"
        run([args.cc, "-std=c11", "-Wall", "-Wextra", *args.cflag, *flags,
             "-I", args.generic_headers, "-I", directory, fixture,
             "-o", program]).check_returncode()
        for case in CASES:
            if variant == "before-ubsan" and case != "large-overflow":
                continue
            if variant == "before-zero" and case not in CASES[:2]:
                continue
            result = run([program, case])
            if variant == "before-zero":
                if result.returncode != 1 or "result=0 polls=1 clocks=0" not in result.stderr:
                    raise RuntimeError(f"The baseline did not reproduce the early return: {case}")
            elif variant == "before-ubsan":
                if result.returncode == 0 or "signed integer overflow" not in result.stderr:
                    raise RuntimeError("The baseline did not reproduce int multiplication overflow")
            else:
                result.check_returncode()
                if result.stdout != f"PASS {case}\n":
                    raise RuntimeError(f"The fixture did not confirm {case}")
    receipt = {"status": "PASS", "cases_per_fixed_variant": len(CASES),
               "scope": "The unchanged extracted function uses controlled poll/EINTR and clock fixtures. GCC automatic-variable zero initialization makes the baseline uninitialized-read consequence deterministic. Normal and ASan/UBSan fixed builds do not use that flag. This is not a target-kernel or CoreFoundation runtime test.",
               "sources": {key: {"path": str(path),
                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                           for key, path in (("before", args.before), ("after", args.after))},
               "commands": records}
    (args.output / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"PASS: {len(CASES)} cases in each of three fixed variants; both baseline failures reproduced")


if __name__ == "__main__":
    main()
