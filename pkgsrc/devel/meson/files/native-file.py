#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Write a Meson native machine file from selected build-machine tools."""

import argparse
import os
import re
import shlex
import tempfile
from pathlib import Path


def meson_string(value):
    """Return a single-quoted Meson literal for a machine-file value."""
    # machinefile.py doubles backslashes before handing values to mparser.
    # That prevents escaping the delimiter, so reject values we cannot encode
    # instead of writing a machine file that Meson will misparse.
    if "'" in value:
        raise ValueError("Meson machine-file strings cannot contain apostrophes")
    return "'" + value + "'"


def meson_array(values):
    return "[" + ", ".join(meson_string(value) for value in values) + "]"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--binary", action="append", default=[])
    parser.add_argument("--cflags", default="")
    parser.add_argument("--cppflags", default="")
    parser.add_argument("--cxxflags", default="")
    parser.add_argument("--ldflags", default="")
    parser.add_argument("--pkg-config-libdir", action="append", default=[])
    args = parser.parse_args()

    binaries = {}
    for entry in args.binary:
        name, separator, path = entry.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            parser.error(f"invalid binary entry: {entry!r}")
        executable = Path(path)
        if not executable.is_absolute() or not executable.is_file() or not executable.stat().st_mode & 0o111:
            parser.error(f"selected build tool is not executable: {path!r}")
        binaries[name] = str(executable)

    lines = ["[binaries]"]
    lines.extend(f"{name} = {meson_string(path)}" for name, path in sorted(binaries.items()))
    lines.extend(("", "[built-in options]"))
    flags = {
        "c_args": shlex.split(args.cflags) + shlex.split(args.cppflags),
        "cpp_args": shlex.split(args.cxxflags) + shlex.split(args.cppflags),
        "c_link_args": shlex.split(args.ldflags),
        "cpp_link_args": shlex.split(args.ldflags),
    }
    if any("'" in value for value in binaries.values()) or any(
            "'" in value for values in flags.values() for value in values):
        parser.error("selected host paths or flags contain an apostrophe that Meson machine files cannot encode")
    lines.extend(f"{name} = {meson_array(values)}" for name, values in flags.items())
    if args.pkg_config_libdir:
        lines.extend(("", "[properties]",
                      f"pkg_config_libdir = {meson_array(args.pkg_config_libdir)}"))
    output = args.output
    content = ("\n".join(lines) + "\n").encode("utf-8")
    if output.is_symlink():
        parser.error(f"native file must not be a symlink: {str(output)!r}")
    if output.is_file() and output.read_bytes() == content:
        return
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    os.replace(temporary, output)


if __name__ == "__main__":
    main()
