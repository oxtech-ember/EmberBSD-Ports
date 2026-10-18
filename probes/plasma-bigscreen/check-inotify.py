#!/usr/bin/env python3
"""Cross-link the real Bigscreen device watcher with and without its provider."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="patched Plasma Bigscreen 6.8.0")
    parser.add_argument("toolchain", type=Path, help="common GCC16 CMake toolchain")
    parser.add_argument("work", type=Path)
    parser.add_argument("--cmake", default="cmake")
    parser.add_argument("--ninja", default="ninja")
    args = parser.parse_args()
    args.source = args.source.resolve()
    args.toolchain = args.toolchain.resolve()
    args.work = args.work.absolute()
    production = (args.source / "inputhandler/CMakeLists.txt").read_text()
    find_line = "find_package(Inotify REQUIRED)"
    if find_line not in production or "    Inotify::Inotify\n" not in production:
        parser.error("the production CMake file does not select Inotify::Inotify")
    if args.work.exists():
        parser.error("work directory already exists")
    args.work.mkdir(parents=True)
    (args.work / "tmp").mkdir()
    environment = dict(os.environ, TMPDIR=str(args.work / "tmp"))
    source = (args.source / "inputhandler").resolve()
    (args.work / "main.cpp").write_text(
        '#include "devicewatcher.h"\n#include <QCoreApplication>\n'
        'int main(int argc, char **argv) { QCoreApplication app(argc, argv); '
        'DeviceWatcher watcher; watcher.recheck(); return 0; }\n')
    (args.work / "CMakeLists.txt").write_text(f'''cmake_minimum_required(VERSION 3.30)
project(bigscreen_inotify LANGUAGES CXX)
if(NOT CMAKE_CROSSCOMPILING OR NOT CMAKE_SYSTEM_NAME STREQUAL "NetBSD"
   OR NOT CMAKE_CXX_COMPILER_ID STREQUAL "GNU"
   OR CMAKE_CXX_COMPILER_VERSION VERSION_LESS "16.2"
   OR NOT CMAKE_CXX_COMPILER_VERSION VERSION_LESS "17")
    message(FATAL_ERROR "Select the common GCC16 EmberBSD cross toolchain")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Qt6 6.11 REQUIRED COMPONENTS Core)
qt_standard_project_setup(REQUIRES 6.11)
find_package(ECM 6.31 REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${{ECM_MODULE_PATH}})
qt_add_executable(watcher main.cpp "{source}/devicewatcher.cpp" "{source}/devicewatcher.h")
target_include_directories(watcher PRIVATE "{source}" "${{CMAKE_SYSROOT}}/usr/pkg/include")
target_link_libraries(watcher PRIVATE Qt6::Core)
if(PORT_INOTIFY)
    {find_line}
    target_link_libraries(watcher PRIVATE Inotify::Inotify)
endif()
''')
    results = {}
    for name, enabled in (("baseline", "OFF"), ("port", "ON")):
        objects = args.work / name
        configure = [args.cmake, "-S", str(args.work), "-B", str(objects),
                     "-G", "Ninja", "--toolchain", str(args.toolchain.resolve()),
                     "-DCMAKE_MAKE_PROGRAM=" + args.ninja,
                     "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-DPORT_INOTIFY=" + enabled]
        build = [args.cmake, "--build", str(objects), "--parallel", "1"]
        for operation, command in (("configure", configure), ("build", build)):
            log_path = args.work / f"{name}-{operation}.log"
            with log_path.open("w") as log:
                result = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
            results[f"{name}-{operation}"] = {"status": result.returncode, "command": command}
            if operation == "configure" and result.returncode:
                raise SystemExit(f"{name} configure failed; inspect {log_path}")
        log = (args.work / f"{name}-build.log").read_text()
        if name == "baseline":
            if not result.returncode or "inotify_" not in log or "undefined reference" not in log:
                raise SystemExit("baseline did not reproduce the missing inotify link")
        elif result.returncode:
            raise SystemExit("the provider did not repair the real watcher link")
    results["watcher-source-sha256"] = hashlib.sha256((source / "devicewatcher.cpp").read_bytes()).hexdigest()
    results["scope"] = "GCC16 target compile/link; no target program execution"
    (args.work / "result.json").write_text(json.dumps(results, indent=2) + "\n")
    print("PASS: original inotify link refused; actual upstream watcher links with its provider")


if __name__ == "__main__":
    main()
