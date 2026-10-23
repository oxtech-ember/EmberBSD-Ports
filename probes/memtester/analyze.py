#!/usr/bin/env python3
# Origin: EmberBSD, AI-assisted by OpenAI Codex (GPT-6).
"""Compare actual AArch64 source analysis before and after the Ports patch."""
import argparse
import collections
import json
from pathlib import Path
import re
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checked", type=Path, required=True,
                   help="completed check.py work directory")
    p.add_argument("--work", type=Path, required=True)
    for name in ("cc", "sysroot", "cppcheck", "clang"):
        p.add_argument("--" + name, required=True)
    a = p.parse_args()
    a.work.mkdir(parents=True, exist_ok=False)
    record = {"commands": [], "versions": {}, "findings": {}}

    def run(cmd, log):
        r = subprocess.run([str(x) for x in cmd], capture_output=True)
        (a.work / log).write_bytes(r.stdout + r.stderr)
        record["commands"].append({"argv": [str(x) for x in cmd], "status": r.returncode})
        return r

    flags = ["-DPOSIX", "-D_POSIX_C_SOURCE=200809L", "-D_FILE_OFFSET_BITS=64",
             "-DTEST_NARROW_WRITES"]
    try:
        for name in ("cc", "cppcheck", "clang"):
            r = run([getattr(a, name), "--version"], name + "-version.log")
            if r.returncode:
                raise RuntimeError(name + " version failed")
            record["versions"][name] = r.stdout.decode().splitlines()[0]
        for variant in ("pristine", "patched"):
            findings = collections.Counter()
            for source in ("memtester.c", "tests.c"):
                prefix = variant + "-" + source
                src = a.checked / variant / source
                pre = a.work / (prefix + ".i")
                gcc = [a.cc, "--sysroot=" + a.sysroot, "-O2", *flags]
                r = run([*gcc, "-fanalyzer", "-Wall", "-Wextra", "-c", src,
                         "-o", a.work / (prefix + ".o")], prefix + "-gcc.log")
                if r.returncode:
                    raise RuntimeError(prefix + " GCC analyzer failed")
                r = run([*gcc, "-E", src, "-o", pre], prefix + "-preprocess.log")
                if r.returncode:
                    raise RuntimeError(prefix + " preprocessing failed")
                r = run([a.cppcheck, "--enable=warning,style,performance,portability",
                         "--error-exitcode=97", "--platform=unix64", "--language=c",
                         "--std=c11", "--check-level=exhaustive", pre], prefix + "-cppcheck.log")
                if r.returncode not in (0, 97):
                    raise RuntimeError(prefix + " Cppcheck failed")
                findings.update(re.findall(r"\[([A-Za-z][A-Za-z0-9_-]*)\]", r.stderr.decode()))
                r = run([a.clang, "--analyze", "--target=aarch64--netbsd",
                         "--sysroot=" + a.sysroot, "-std=gnu17", *flags,
                         "-Xanalyzer", "-analyzer-output=text", src,
                         "-o", a.work / (prefix + ".plist")], prefix + "-csa.log")
                if r.returncode:
                    raise RuntimeError(prefix + " CSA failed")
                findings.update("CSA:" + name for name in re.findall(r"warning: .*?\[([^]]+)\]", r.stderr.decode()))
            record["findings"][variant] = dict(findings)
        harness = Path(__file__).with_name("bitspread.c")
        inc = ["-I", a.checked / "patched"]
        pre = a.work / "bitspread.i"
        gcc = [a.cc, "--sysroot=" + a.sysroot, "-O2", *flags, *inc]
        r = run([*gcc, "-fanalyzer", "-Wall", "-Wextra", "-c", harness,
                 "-o", a.work / "bitspread.o"], "bitspread-gcc.log")
        if r.returncode:
            raise RuntimeError("regression GCC analysis failed")
        r = run([*gcc, "-E", harness, "-o", pre], "bitspread-preprocess.log")
        if r.returncode:
            raise RuntimeError("regression preprocessing failed")
        r = run([a.cppcheck, "--enable=warning,style,performance,portability",
                 "--error-exitcode=97", "--platform=unix64", "--language=c",
                 "--std=c11", "--check-level=exhaustive", pre], "bitspread-cppcheck.log")
        if r.returncode not in (0, 97):
            raise RuntimeError("regression Cppcheck failed")
        record["regression_findings"] = dict(collections.Counter(
            re.findall(r"\[([A-Za-z][A-Za-z0-9_-]*)\]", r.stderr.decode())))
        # The harness includes tests.c, so only that file's inherited findings remain.
        if collections.Counter(record["regression_findings"]) - collections.Counter(record["findings"]["patched"]):
            raise RuntimeError("regression adds Cppcheck findings")
        r = run([a.clang, "--analyze", "--target=aarch64--netbsd",
                 "--sysroot=" + a.sysroot, "-std=gnu17", *flags, *inc,
                 "-Xanalyzer", "-analyzer-output=text", harness,
                 "-o", a.work / "bitspread.plist"], "bitspread-csa.log")
        if r.returncode or r.stderr:
            raise RuntimeError("regression CSA needs review")
        before = collections.Counter(record["findings"]["pristine"])
        after = collections.Counter(record["findings"]["patched"])
        if before["shiftTooManyBits"] != 4 or after["shiftTooManyBits"] != 0:
            raise RuntimeError("expected four upstream oversized shifts, none after patch")
        if after - before:
            raise RuntimeError("new Cppcheck findings need review")
        record["status"] = "pass"
        print("PASS: four oversized shifts removed; no new Cppcheck findings; GCC/CSA completed")
    finally:
        (a.work / "verification.json").write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
