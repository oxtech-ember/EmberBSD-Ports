#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the export preflight for the ncurses patch.
import json
from pathlib import Path
import shutil
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: ncurses-export-guard.py NEW_WORK")
work = Path(sys.argv[1])
assert work.is_absolute() and not work.exists() and not work.is_symlink()
root = Path(__file__).resolve().parents[3]
name = "pkgsrc-ncurses-native-headers.patch"
line = "patch\tprofiles/common-build-tools/patches/" + name + "\n"
export = (root / "pkgsrc/export.conf").read_text()
assert export.count(name) == 1 and line in export, "Require one export selection"
# A fixture repository with this one patch and no recipes.
fixture = work / "fixture"
patches = fixture / "profiles/common-build-tools/patches"
patches.mkdir(parents=True)
(fixture / "scripts").mkdir()
(fixture / "pkgsrc").mkdir()
shutil.copy2(root / "scripts/prepare-pkgsrc.sh", fixture / "scripts/prepare-pkgsrc.sh")
(fixture / "pkgsrc/export.conf").write_text(line)
(patches / name).symlink_to(root / "profiles/common-build-tools/patches" / name)
commands = []
for label, message in [("present", "Initialize the pinned submodule"),
                       ("missing", "Missing infrastructure patch: profiles/common-build-tools/patches/" + name)]:
    if label == "missing":
        (patches / name).unlink()
    argv = ["sh", str(fixture / "scripts/prepare-pkgsrc.sh"), str(work / label)]
    result = subprocess.run(argv, capture_output=True, text=True)
    commands.append(dict(case=label, argv=argv, exit=result.returncode, stdout=result.stdout, stderr=result.stderr))
    # The fixture has no pinned upstream tree, so the present case stops
    # after the preflight.
    assert result.returncode == 2 and message in result.stderr, commands[-1]
    assert not (work / label).exists()
(work / "result.json").write_text(json.dumps(dict(scope="Export preflight with the ncurses native-header patch present and missing; no complete export or package build.", commands=commands), indent=2) + "\n")
print("PASS: the export preflight requires the ncurses native-header patch")
