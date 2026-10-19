#!/usr/bin/env python3
"""Check the LXQt cross recipe's non-executed target-tool contract."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("recipe", type=Path)
    parser.add_argument("sysroot", type=Path)
    args = parser.parse_args()
    recipe = args.recipe.resolve()
    sysroot = args.sysroot.resolve()
    makefile = (recipe / "Makefile").read_text()
    target_tool = sysroot / "usr/pkg/bin/xdg-user-dirs-update"

    if "-DXdgUserDirsUpdate_EXECUTABLE:FILEPATH=${PREFIX}/bin/xdg-user-dirs-update" not in makefile:
        raise SystemExit("cross CMake configuration does not use the target command path")
    if "${TEST} -x ${CROSS_DESTDIR}${PREFIX}/bin/xdg-user-dirs-update" not in makefile:
        raise SystemExit("cross configuration does not validate the target command")
    if "DEPENDS+=\txdg-user-dirs-[0-9]*:../../x11/xdg-user-dirs" not in makefile:
        raise SystemExit("the target command provider is not a runtime dependency")
    if not target_tool.is_file() or not target_tool.stat().st_mode & 0o111:
        raise SystemExit(f"target executable is missing from the sysroot: {target_tool}")

    print("LXQt target-only XdgUserDirs path and runtime provider checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
