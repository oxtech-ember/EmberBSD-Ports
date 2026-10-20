#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Configure both real KWin demos with the production cross-cache transfer."""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
from pathlib import Path

CONTEXT = """CMAKE_TOOLCHAIN_FILE CMAKE_SYSTEM_NAME CMAKE_SYSTEM_PROCESSOR
CMAKE_C_COMPILER CMAKE_CXX_COMPILER CMAKE_SYSROOT CMAKE_FIND_ROOT_PATH
CMAKE_FIND_ROOT_PATH_MODE_PROGRAM CMAKE_FIND_ROOT_PATH_MODE_LIBRARY
CMAKE_FIND_ROOT_PATH_MODE_INCLUDE CMAKE_FIND_ROOT_PATH_MODE_PACKAGE
CMAKE_PREFIX_PATH CMAKE_C_FLAGS CMAKE_CXX_FLAGS CMAKE_EXE_LINKER_FLAGS
ECM_DIR Qt6_DIR QT_HOST_PATH QT_HOST_PATH_CMAKE_DIR Qt6CoreTools_DIR
Qt6GuiTools_DIR PKG_CONFIG_EXECUTABLE WaylandScanner_EXECUTABLE
WaylandProtocols_DATADIR""".split()


def quoted(value):
    if "]==]" in value:
        raise ValueError("CMake cache value contains a bracket delimiter")
    return "[==[" + value + "]==]"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--parent-cache", type=Path, required=True)
    parser.add_argument("--tests-cmake", type=Path)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--cmake", required=True)
    parser.add_argument("--sdk-source", required=True)
    args = parser.parse_args()
    ports = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(ports / "profiles/development-toolchain/runtime/recipe/files"))
    import sdk_source
    sdk_source.load(args.sdk_source)
    sdk_source.install_signal_handlers()
    from emberbsd_sdk.process import run_logged
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError

    work = args.work.absolute()
    if work.exists() or work.is_symlink():
        raise ValueError("Select a new work directory")
    source = args.source.resolve(strict=True)
    production = args.tests_cmake or source / "tests/CMakeLists.txt"
    text = production.read_text()
    marker = "function (kwin_add_demo name)"
    if text.count(marker) != 1:
        raise ValueError("The KWin external-demo contract changed")
    fragment = text.split(marker)[0]
    values = {}
    for line in args.parent_cache.read_text().splitlines():
        if line and not line.startswith(("#", "//")) and "=" in line:
            declaration, value = line.split("=", 1)
            key = declaration.split(":", 1)[0]
            if key in CONTEXT:
                values[key] = value
    for key in ("CMAKE_SYSTEM_NAME", "CMAKE_SYSROOT", "CMAKE_C_COMPILER",
                "CMAKE_CXX_COMPILER", "Qt6CoreTools_DIR", "Qt6GuiTools_DIR"):
        if not values.get(key) or values[key].endswith("-NOTFOUND"):
            raise ValueError("Missing accepted parent input: " + key)
    work.mkdir(parents=True)
    fixture = work / "context"
    fixture.mkdir()
    (fixture / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.20)\n"
        "project(kwin_demo_context LANGUAGES NONE)\n" + fragment)
    seed = work / "parent.cmake"
    seed.write_text("".join("set(" + key + " " + quoted(value) +
                           ' CACHE STRING "Accepted parent")\n'
                           for key, value in values.items()))
    receipt = {"production": str(production),
               "production_sha256": hashlib.sha256(text.encode()).hexdigest(),
               "parent_cache_sha256": hashlib.sha256(args.parent_cache.read_bytes()).hexdigest(),
               "source": str(source), "commands": [], "status": "running"}
    code = 0
    try:
        commands = [[args.cmake, "-S", str(fixture), "-B", str(work / "cross"), "-C", str(seed)]]
        for demo in ("fractional-scaling", "pip"):
            commands.append([args.cmake, "-C" + str(work / "cross/cross-demo-cache.cmake"),
                             "-GUnix Makefiles", "-S", str(source / "tests" / demo),
                             "-B", str(work / demo)])
        commands.append([args.cmake, "-S", str(fixture), "-B", str(work / "native")])
        for index, argv in enumerate(commands):
            receipt["commands"].append(argv)
            run_logged(argv, work / (str(index) + ".log"))
        if (work / "native/cross-demo-cache.cmake").exists():
            raise ValueError("Native configuration unexpectedly created a cross cache")
        receipt["status"] = "both-real-demos-configured-native-transfer-absent"
    except CommandError as error:
        code = error.returncode
        receipt.update(status="configure-failed", error=str(error))
    except ProcessOwnershipError as error:
        code = 1
        receipt.update(status="ownership-unproven", sid=error.sid, error=str(error))
    finally:
        (work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["status"])
    return code


if __name__ == "__main__":
    sys.exit(main())
