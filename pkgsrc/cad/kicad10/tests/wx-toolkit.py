#!/usr/bin/env python3
"""Exercise KiCad's real toolkit selection with the installed wx provider."""

import argparse
from pathlib import Path
import subprocess


def bracket(value):
    marker = "="
    while "]" + marker + "]" in str(value):
        marker += "="
    return "[" + marker + "[" + str(value) + "]" + marker + "]"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--wx-config", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--cmake", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    source = (args.source / "CMakeLists.txt").read_text()
    start = source.index("# Check if '--toolkit=xxx' option has been passed")
    end = source.index("# Require the same wxWidgets version", start)
    selection = source[start:end]

    # The Unix success cases execute KiCad's FindwxWidgets module and the real
    # installed wx-config. The others check platform and wxPython selection.
    cases = (
        ("unix-default", False, False, "", "", True, False),
        ("unix-explicit", False, False, "", "gtk4", True, False),
        ("apple-provider", True, False, "", "", False, False),
        ("python-match", False, True, "gtk4", "gtk4", True, False),
        ("python-mismatch", False, True, "gtk4", "gtk3", False, True),
    )
    for name, apple, python, pytoolkit, requested, find, failure in cases:
        directory = args.work / name
        directory.mkdir(parents=True, exist_ok=True)
        text = "cmake_minimum_required(VERSION 3.20)\nproject(toolkit NONE)\n"
        values = {
            "UNIX": "TRUE", "APPLE": "TRUE" if apple else "FALSE",
            "KICAD_SCRIPTING_WXPYTHON": "TRUE" if python else "FALSE",
            "WXPYTHON_TOOLKIT": pytoolkit,
            "wxWidgets_CONFIG_EXECUTABLE": args.wx_config.resolve(),
        }
        for key, value in values.items():
            text += f"set({key} {bracket(value)})\n"
        text += "set(wxWidgets_CONFIG_OPTIONS " + bracket(
            f"--prefix={args.prefix};--exec-prefix={args.prefix}") + ")\n"
        if requested:
            text += f"list(APPEND wxWidgets_CONFIG_OPTIONS --toolkit={requested})\n"
        text += selection
        if find:
            text += "list(PREPEND CMAKE_MODULE_PATH " + bracket(
                args.source.resolve() / "cmake") + ")\n"
            text += "set(wxWidgets_USE_STATIC OFF)\n"
            text += "find_package(wxWidgets 3.2 REQUIRED COMPONENTS gl aui adv html core net base propgrid xml stc richtext webview)\n"
            text += "if(NOT _wx_selected_config MATCHES \"gtk4\")\nmessage(FATAL_ERROR \"GTK4 was not selected\")\nendif()\n"
        elif apple:
            text += "if(wxWidgets_CONFIG_OPTIONS MATCHES \"--toolkit=\")\nmessage(FATAL_ERROR \"Provider selection was overwritten\")\nendif()\n"
        (directory / "CMakeLists.txt").write_text(text)
        result = subprocess.run(
            [str(args.cmake), "-S", str(directory), "-B", str(directory / "build")],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=120, check=False,
        )
        (directory / "configure.log").write_text(result.stdout)
        if failure:
            if result.returncode == 0 or "must use the same toolkit" not in result.stdout:
                raise SystemExit(f"{name}: mismatch was not rejected; see configure.log")
        elif result.returncode:
            raise SystemExit(f"{name}: configuration failed; see configure.log")
        print(f"{name}: PASS")


if __name__ == "__main__":
    main()
