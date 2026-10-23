#!/usr/bin/env python3
# Origin: EmberBSD, AI-assisted by OpenAI Codex (GPT-6).
"""Check the actual memtester Bit Spread generator with a native GCC16."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import resource
import signal
import subprocess

HERE = Path(__file__).resolve().parent
PATCH = HERE.parents[1] / "pkgsrc/sysutils/memtester/patches/patch-tests.c"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--cc", required=True)
    parser.add_argument("--cflag", action="append", default=[])
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    record = {"commands": [], "inputs": {}, "status": "started"}

    def run(command, name, expected=0):
        result = subprocess.run([str(c) for c in command], capture_output=True)
        (args.work / (name + ".log")).write_bytes(result.stdout + result.stderr)
        record["commands"].append({"argv": [str(c) for c in command],
                                   "status": result.returncode})
        if expected is not None and result.returncode != expected:
            raise RuntimeError(f"{name}: exit {result.returncode}, expected {expected}")
        return result

    try:
        version = run([args.cc, "--version"], "compiler").stdout.decode()
        if not any("16." in line for line in version.splitlines()[:1]):
            raise RuntimeError("GCC16 is required")
        for name in ("tests.c", "types.h", "sizes.h", "memtester.h", "memtester.c", "tests.h"):
            record["inputs"][name] = hashlib.sha256((args.source / name).read_bytes()).hexdigest()
        record["inputs"]["patch"] = hashlib.sha256(PATCH.read_bytes()).hexdigest()
        record["inputs"]["regression"] = hashlib.sha256((HERE / "bitspread.c").read_bytes()).hexdigest()
        for name in ("pristine", "patched"):
            dest = args.work / name
            dest.mkdir()
            for source in record["inputs"]:
                if source.endswith((".c", ".h")):
                    shutil.copy2(args.source / source, dest / source)
        run(["patch", "-d", args.work / "patched", "-p0", "-i", PATCH], "patch")
        base = [args.cc, *args.cflag, "-O2", "-Wall", "-Wextra", "-fanalyzer"]

        def check(source, label, fail=False):
            binary = args.work / label
            run([*base, "-I", source, HERE / "bitspread.c", "-o", binary], label + "-build")
            result = run([binary], label, expected=None)
            if fail:
                if result.returncode != 1 or b"FAIL: " not in result.stderr:
                    raise RuntimeError(f"{label}: regression did not detect the fault")
            elif result.returncode != 0 or b"PASS: " not in result.stderr:
                raise RuntimeError(f"{label}: regression failed")

        check(args.work / "pristine", "red", fail=True)
        check(args.work / "patched", "green")
        text = (args.work / "patched/tests.c").read_text()
        mutants = {
            "loop": ("j < (UL_LEN - 2) * 2", "j < UL_LEN * 2"),
            "turn": ("j < UL_LEN - 2", "j < UL_LEN - 1"),
            "reverse": ("UL_LEN * 2 - 5 - j", "UL_LEN * 2 - 4 - j"),
            "complement": ("UL_ONEBITS ^ ((ONE << j)", "UL_ONEBITS ^ ((ONE << (j + 1))"),
        }
        for name, (old, new) in mutants.items():
            dest = args.work / ("mutant-" + name)
            shutil.copytree(args.work / "patched", dest)
            if old not in text:
                raise RuntimeError(f"{name}: mutation site missing")
            (dest / "tests.c").write_text(text.replace(old, new))
            check(dest, name, fail=True)
        for name in ("pristine", "patched"):
            binary = args.work / ("ubsan-" + name)
            run([*base, "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
                 "-I", args.work / name, HERE / "bitspread.c", "-o", binary],
                "ubsan-" + name + "-build")
            result = run([binary], "ubsan-" + name, expected=None)
            wanted = (-signal.SIGILL, -signal.SIGTRAP) if name == "pristine" else (0,)
            if result.returncode not in wanted:
                raise RuntimeError(f"ubsan-{name}: unexpected status {result.returncode}")
        binary = args.work / "memtester"
        run([*base, "-DTEST_NARROW_WRITES", args.work / "patched/memtester.c",
             args.work / "patched/tests.c", "-o", binary], "memtester-build")
        run([binary, "1M", "1"], "memtester-smoke")
        record["binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
        record["status"] = "pass"
        print("PASS: real-source RED/GREEN, four causal mutants, UBSan trap pair, complete 1 MiB/one-loop smoke")
    finally:
        (args.work / "verification.json").write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
