#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run the staged GYP scripts with their package Python after prefix relocation."""
import ast
import os
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve(strict=True)
python = Path("bin") / sys.argv[2]
for script in sorted(root.rglob("*.py")):
    source = script.read_bytes()
    if not source.startswith(b"#!/usr/bin/env python"):
        continue
    lines = source.decode("utf-8").splitlines(keepends=True)
    tree = ast.parse(source)
    # Keep the module docstring and the required placement of future imports
    # when introducing the shell/Python launcher as Python's first string.
    doc = ast.get_docstring(tree, clean=False)
    insert_at = 1
    if doc is not None:
        stmt = tree.body[0]
        lines[stmt.lineno - 1:stmt.end_lineno] = ["\n"] * (stmt.end_lineno - stmt.lineno + 1)
        insert_at = stmt.end_lineno
    for stmt in tree.body:
        if isinstance(stmt, ast.ImportFrom) and stmt.module == "__future__":
            insert_at = stmt.end_lineno
    declaration = "__doc__ = None\n" if doc is None else (
        f"__doc__ = {doc!r} if __import__('sys').flags.optimize < 2 else None\n")
    lines.insert(insert_at, declaration)
    level = Path("share/gyp") / script.relative_to(root).parent
    interpreter = os.path.relpath(python, level)
    lines[:1] = ["#!/bin/sh\n", "'''exec' \"$(dirname \"$0\")/" + interpreter + "\" -B \"$0\" \"$@\"\n", "' '''\n"]
    rewritten = "".join(lines)
    compile(rewritten, str(script), "exec")
    script.write_text(rewritten, encoding="utf-8")

# Python caches modules next to the imported filename. Real site-package
# directories keep that cache outside the verified source, with one copy of
# every module shared by the generator and Python importers.
site = Path(sys.argv[3])
modules = root / "pylib/gyp"
site.mkdir(parents=True, exist_ok=True)
for item in sorted(modules.rglob("*")):
    installed = site / item.relative_to(modules)
    if item.is_dir() and not item.is_symlink():
        installed.mkdir()
    else:
        installed.symlink_to(os.path.relpath(item, installed.parent))
