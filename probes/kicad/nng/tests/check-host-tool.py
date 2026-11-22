#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Query the host tools and optional documentation inputs of an NNG recipe."""
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", required=True, type=Path)
    parser.add_argument("--makeconf", required=True, type=Path)
    parser.add_argument("--bmake", required=True, type=Path)
    args = parser.parse_args()
    for option, docs in (("doc", True), ("-doc", False)):
        cmd = [args.bmake, "-C", args.pkgsrc / "net/nng", f"MAKECONF={args.makeconf}",
               f"PKG_OPTIONS.nng={option}", "-v", "TOOL_DEPENDS", "-v", "DISTFILES",
               "-v", "TOOL_PYTHONBIN"]
        tools, sources, python = subprocess.check_output(cmd, text=True).splitlines()
        assert ("lowdown>=3.2.1:../../textproc/lowdown" in tools) == docs
        assert ("nng-docs-" in sources) == docs
        if docs:
            assert Path(python).is_absolute()
        print(f"Checked option {option}")


if __name__ == "__main__":
    main()
