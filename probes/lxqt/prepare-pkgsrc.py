#!/usr/bin/env python3
"""Export the common profile and the tracked LXQt recipe overlay."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    source = root / "probes/lxqt/recipes"
    tracked = set(subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "--", "probes/lxqt/recipes"],
        text=True).splitlines())
    files = sorted(p for p in source.rglob("*") if p.is_file())
    if any(p.is_symlink() for p in source.rglob("*")):
        parser.error("The LXQt overlay must not contain symbolic links")
    if any(p.relative_to(root).as_posix() not in tracked for p in files):
        parser.error("Commit every LXQt recipe file before export")
    subprocess.run(["sh", str(root / "scripts/prepare-pkgsrc.sh"),
                    str(args.destination)], check=True)
    for path in files:
        target = args.destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    receipt = {
        "ports": subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "overlay": [p.relative_to(source).as_posix() for p in files],
    }
    (args.destination / "EMBERBSD-LXQT-RECIPES.json").write_text(
        json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
