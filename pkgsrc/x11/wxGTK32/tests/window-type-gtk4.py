#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run actual GTK4 EWMH helper definitions with native GObject lifetime checks.

Only the GtkWindow mapped/display boundary is modeled; GObject qdata ownership,
replacement, and cleanup are exercised against the native GObject runtime.
This is not window-manager, Wayland protocol, or GUI acceptance.
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


def definition(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth, end = 1, brace + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end] + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--cxx", required=True)
    parser.add_argument("--pkg-config", required=True)
    parser.add_argument("--work-parent", type=Path, required=True)
    parser.add_argument("--cxx-flag", action="append", default=[])
    args = parser.parse_args()
    source = args.source.read_text()
    helpers = "\n".join(definition(source, signature) for signature in (
        "inline bool RequestWindowType(GtkWindow* window, const char* typeAtom)",
        "inline const char* GetRequestedWindowType(GtkWindow* window)"))
    harness = Path(__file__).with_name("window-type-gtk4-harness.cpp").read_text()
    harness = harness.replace("// PRODUCTION_WINDOW_TYPE_HELPERS",
                              "namespace wxGTKWindowState4 {\n" + helpers + "\n}")
    flags = shlex.split(subprocess.check_output(
        [args.pkg_config, "--cflags", "--libs", "gobject-2.0"], text=True))
    with tempfile.TemporaryDirectory(prefix="wx-window-type-", dir=args.work_parent) as work:
        cpp, exe = Path(work) / "contract.cpp", Path(work) / "contract"
        cpp.write_text(harness)
        subprocess.run([args.cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        *args.cxx_flag,
                        str(cpp), *flags, "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True, timeout=20,
                       env={**os.environ, "G_DEBUG": "fatal-criticals"})


if __name__ == "__main__":
    main()
