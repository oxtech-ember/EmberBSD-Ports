#!/usr/bin/env python3
"""Keep installed qmake specs independent of the host's build prefix."""

from pathlib import Path


PKGDIR = Path(__file__).resolve().parents[1]
MAKEFILE = (PKGDIR / "Makefile").read_text(encoding="utf-8")

for name in ("qmake.conf", "qmake.conf.mac"):
    text = (PKGDIR / "files" / name).read_text(encoding="utf-8")
    entries = [line.split("=", 1)[1].strip() for line in text.splitlines()
               if line.split("=", 1)[0].strip() == "QMAKE_MKDIR"]
    if entries != ["mkdir -p"]:
        raise SystemExit(f"{name}: QMAKE_MKDIR must use the target PATH")
    if "@MKDIR@" in text:
        raise SystemExit(f"{name}: host MKDIR substitution remains in template")

if "@MKDIR@" in MAKEFILE or "s:@MKDIR@:" in MAKEFILE:
    raise SystemExit("Makefile still substitutes the selected host MKDIR into qmake specs")
if "${MKDIR}" not in MAKEFILE:
    raise SystemExit("recipe no longer uses pkgsrc's selected MKDIR for its build commands")

print("PASS: installed qmake specs resolve mkdir through the target PATH")
