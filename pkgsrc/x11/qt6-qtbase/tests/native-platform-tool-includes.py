#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check a Darwin Qt platform tool against the installed Qtbase targets."""

import argparse
from pathlib import Path
import subprocess
import tempfile


PROJECT = """\
cmake_minimum_required(VERSION 3.25)
project(consumer LANGUAGES CXX)
find_package(Threads REQUIRED)
include("${QT_PREFIX}/lib/cmake/Qt6/Qt6Targets.cmake")
get_target_property(common Qt6::PlatformCommonInternal INTERFACE_INCLUDE_DIRECTORIES)
get_target_property(tool Qt6::PlatformToolInternal INTERFACE_INCLUDE_DIRECTORIES)
if(NOT QT_USER_INCLUDE IN_LIST common)
    message(FATAL_ERROR "Qt lost the configured user include directory")
endif()
foreach(path IN LISTS common tool)
    if(path MATCHES "[.]sdk/usr/include/?$")
        message(FATAL_ERROR "Qt exported an Apple SDK include directory")
    endif()
endforeach()
add_library(consumer STATIC consumer.cpp)
target_link_libraries(consumer PRIVATE Qt6::PlatformToolInternal)
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cmake", "ninja", "cxx", "qt-prefix", "user-include", "sdk"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--ar", type=Path, required=True)
    parser.add_argument("--ranlib", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        (work / "CMakeLists.txt").write_text(PROJECT)
        (work / "consumer.cpp").write_text("int consumer() { return 0; }\n")
        build = work / "build"
        subprocess.run([
            args.cmake, "-S", work, "-B", build, "-G", "Ninja",
            "-DCMAKE_MAKE_PROGRAM=" + str(args.ninja),
            "-DCMAKE_CXX_COMPILER=" + str(args.cxx),
            "-DCMAKE_AR=" + str(args.ar),
            "-DCMAKE_RANLIB=" + str(args.ranlib),
            "-DCMAKE_OSX_SYSROOT=" + str(args.sdk),
            "-DQT_PREFIX=" + str(args.qt_prefix.resolve()),
            "-DQT_USER_INCLUDE=" + str(args.user_include),
        ], check=True)
        subprocess.run([args.cmake, "--build", build], check=True)


if __name__ == "__main__":
    main()
