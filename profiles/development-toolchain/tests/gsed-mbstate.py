#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise real GNU sed state initialization in byte and UTF-8 locales."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: gsed-mbstate.py ABSOLUTE_SED NEW_RESULTS_DIRECTORY")
    sed = pathlib.Path(sys.argv[1])
    work = pathlib.Path(sys.argv[2])
    if not sed.is_absolute() or not work.is_absolute() or not sed.is_file():
        raise SystemExit("Absolute executable and result paths are required")
    work.mkdir()
    cases = []
    for locale in ("C", os.environ.get("UTF8_LOCALE", "en_US.UTF-8")):
        cases.extend([
            (locale, "ascii-substitution", "s/x/y/", b"x\n", b"y\n", 0),
            (locale, "patch-byte-filter", "/[$]NetBSD.*/d",
             b"alpha\n$NetBSD: fixture $\nbeta\n", b"alpha\nbeta\n", 0),
            (locale, "address-range", "/alpha/,/beta/d",
             b"before\nalpha\ninside\nbeta\nafter\n", b"before\nafter\n", 0),
        ])
    locale = os.environ.get("UTF8_LOCALE", "en_US.UTF-8")
    cases.extend([
        (locale, "utf8-character-count", "s/./x/g", "αβ\n".encode(), b"xx\n", 0),
        (locale, "utf8-transliteration", "y/αβ/γδ/", "αβ\n".encode(), "γδ\n".encode(), 0),
        (locale, "utf8-replacement-escape", r"s/x/\xCE\xA3/", b"x\n", "Σ\n".encode(), 0),
        (locale, "utf8-lowercase", r"s/.*/\L&/", "Σ\n".encode(), "σ\n".encode(), 0),
        (locale, "utf8-uppercase", r"s/.*/\U&/", "α\n".encode(), "Α\n".encode(), 0),
        (locale, "invalid-multibyte-delimiter", "sΣxΣyΣ", b"x\n", b"", 1),
        (locale, "invalid-utf8-input", "s/./x/g", b"a\xffb\n", b"x\xffx\n", 0),
    ])
    results = []
    for index, (locale, name, program, data, expected, status) in enumerate(cases):
        env = dict(os.environ, LC_ALL=locale)
        proc = subprocess.run([str(sed), "-e", program], input=data,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        passed = proc.returncode == status and proc.stdout == expected
        if status == 0:
            passed = passed and not proc.stderr
        else:
            passed = passed and bool(proc.stderr)
        # Fixed independent digest of the hand-written filtered byte fixture.
        if name == "patch-byte-filter":
            passed = passed and hashlib.sha1(proc.stdout).hexdigest() == "9269a71477ce057095d7e6bb5238b4bd6e13c051"
        (work / f"{index:02d}-{name}.stdout").write_bytes(proc.stdout)
        (work / f"{index:02d}-{name}.stderr").write_bytes(proc.stderr)
        results.append({"locale": locale, "case": name, "passed": passed,
                        "exit": proc.returncode, "expected_exit": status})
        print(("PASS" if passed else "FAIL") + ": " + locale + " " + name)
    summary = {"total": len(results), "passed": sum(r["passed"] for r in results),
               "failed": sum(not r["passed"] for r in results), "results": results}
    (work / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"{summary['passed']}/{summary['total']} cases passed")
    return bool(summary["failed"])


if __name__ == "__main__":
    raise SystemExit(main())
