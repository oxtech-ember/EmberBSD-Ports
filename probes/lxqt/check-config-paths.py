#!/usr/bin/env python3
"""Check native relocation and target paths in the staged LXQt modules."""

import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prefix", type=Path, help="prefix from build-host-tools.py")
    parser.add_argument("--cmake", required=True)
    parser.add_argument("--ninja", required=True)
    args = parser.parse_args()
    prefix = args.prefix.resolve()
    cases = [
        ("native", [], prefix / "share", prefix / "share", prefix / "etc/xdg"),
        ("cross", ["-DCMAKE_SYSTEM_NAME=NetBSD", "-DCMAKE_INSTALL_PREFIX=/usr/pkg"],
         Path("/usr/pkg/share"), Path("/usr/pkg/share"), Path("/usr/pkg/etc/xdg")),
        ("custom", ["-DCMAKE_SYSTEM_NAME=NetBSD", "-DCMAKE_INSTALL_PREFIX=/opt/target",
                    "-DCMAKE_INSTALL_DATAROOTDIR=assets", "-DCMAKE_INSTALL_DATADIR=metadata",
                    "-DLXQT_ETC_XDG_DIR=/etc/xdg"],
         Path("/opt/target/assets"), Path("/opt/target/metadata"), Path("/etc/xdg")),
    ]
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory)
        (source / "CMakeLists.txt").write_text("""cmake_minimum_required(VERSION 3.18)
project(check_lxqt_paths NONE)
find_package(lxqt2-build-tools CONFIG REQUIRED)
include(LXQtConfigVars)
get_directory_property(definitions COMPILE_DEFINITIONS)
file(WRITE "${CMAKE_BINARY_DIR}/paths" "${LXQT_SHARE_DIR}\n${LXQT_TRANSLATIONS_DIR}\n"
     "${LXQT_GRAPHICS_DIR}\n${LXQT_DATA_DIR}\n${LXQT_ETC_XDG_DIR}\n${definitions}")
""")
        for name, options, share, data, xdg in cases:
            build = source / name
            subprocess.run([args.cmake, "-S", source, "-B", build, "-G", "Ninja",
                            "-DCMAKE_MAKE_PROGRAM=" + args.ninja, "-DCMAKE_INSTALL_LIBDIR=lib",
                            "-Dlxqt2-build-tools_DIR=" + str(prefix / "share/cmake/lxqt2-build-tools"),
                            *options], check=True)
            *paths, definitions = (build / "paths").read_text().splitlines()
            expected = [share / "lxqt", share / "lxqt/translations", share / "lxqt/graphics", data, xdg]
            macros = ["LXQT_SHARE_DIR", "LXQT_SHARE_TRANSLATIONS_DIR", "LXQT_GRAPHICS_DIR",
                      "LXQT_DATA_DIR", "LXQT_ETC_XDG_DIR"]
            if paths != list(map(str, expected)) or any(
                    f'{macro}="{path}"' not in definitions.split(";")
                    for macro, path in zip(macros, expected)):
                raise SystemExit(f"{name}: unexpected LXQt paths or compile definitions: {paths} {definitions}")


if __name__ == "__main__":
    main()
