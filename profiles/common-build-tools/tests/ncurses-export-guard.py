#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the exact export preflight block.
import json
from pathlib import Path
import re
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: ncurses-export-guard.py NEW_WORK")
work = Path(sys.argv[1])
assert work.is_absolute() and not work.exists() and not work.is_symlink()
root = Path(__file__).resolve().parents[3]
script = (root / "scripts/prepare-pkgsrc.sh").read_text()
name = "pkgsrc-ncurses-native-headers.patch"
assert script.count(name) == 2, "Require preflight and application selections"
block = re.search(r'    for delta in [^\n]+; do\n        \[ -s "\$root/profiles/common-build-tools/patches/\$delta" \] \|\| \{\n.*?\n    done\n', script, re.S)
assert block and name in block.group()
patches = work / "profiles/common-build-tools/patches"
patches.mkdir(parents=True)
for patch in (root / "profiles/common-build-tools/patches").iterdir():
    if patch.is_file():
        (patches / patch.name).symlink_to(patch)
commands = []
for label, expected in [("present", 0), ("missing", 2)]:
    if label == "missing":
        (patches / name).unlink()
    argv = ["/bin/sh", "-c", 'set -eu; root=$1;\n' + block.group(), "preflight", str(work)]
    result = subprocess.run(argv, capture_output=True, text=True)
    commands.append(dict(case=label, argv=argv, exit=result.returncode, stdout=result.stdout, stderr=result.stderr))
    assert result.returncode == expected, commands[-1]
    if label == "missing":
        assert "Missing common-tools infrastructure patch: " + name in result.stderr
(work / "result.json").write_text(json.dumps(dict(scope="Exact common-tools preflight block and both canonical delta selections; no complete export or package build.", commands=commands), indent=2) + "\n")
print("PASS: exact export preflight requires the ncurses native-header patch")
