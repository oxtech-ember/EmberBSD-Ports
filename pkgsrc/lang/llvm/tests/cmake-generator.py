#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the LLVM generator in a prepared SDK pkgsrc tree."""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pkgsrc", "makeconf", "host-prefix", "work"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    tools = args.host_prefix.resolve() / "bin"
    env = dict(os.environ, MAKECONF=str(args.makeconf.resolve()), SHELL=str(tools / "mksh"))

    with tempfile.TemporaryDirectory(dir=args.work) as temporary:
        work = Path(temporary).resolve()

        def query(expected, *options, package="lang/llvm"):
            command = [tools / "bmake", "-C", args.pkgsrc / package,
                       "WRKDIR=" + str(work), *options, "show-vars",
                       "VARNAMES=_CMAKE_BUILD_SYSTEM WRKSRC CONFIGURE_DIR CMAKE_BUILD_DIR INSTALL_TARGET"]
            system, source, configure_dir, subdir, install = subprocess.check_output(
                command, env=env, text=True).splitlines()
            assert system == expected, (package, options, system, expected)
            return Path(source) / configure_dir / subdir, install

        build, install = query("Ninja")
        query("Unix Makefiles", "CMAKE_GENERATOR=make")
        query("Unix Makefiles", "CMAKE_GENERATORS_INCOMPATIBLE=ninja")
        query("Ninja", package="lang/llvm-devel")
        query("Unix Makefiles", "MAKECONF=/dev/null", "USE_CROSS_COMPILE=no",
              "EMBERBSD_SDK_SOURCE=", package="x11/kf6-kwidgetsaddons")
        for package in ("lang/mlir", "lang/flang", "lang/flang-rt", "devel/protobuf", "devel/protobuf-devel",
                        "multimedia/assimp", "x11/kf6-kwidgetsaddons",
                        "textproc/kf6-sonnet-parsetrigrams", "textproc/kf6-syntax-highlighting-indexer"):
            previous, _ = query("Ninja", package=package)
            previous.mkdir(parents=True, exist_ok=True)
            cache = previous / "CMakeCache.txt"
            cache.write_text("CMAKE_GENERATOR:INTERNAL=Unix Makefiles\n")
            try:
                query("Unix Makefiles", package=package)
            finally:
                cache.unlink()
        source = work / "source"
        source.mkdir()
        (source / "stage.c").write_text("int llvm_stage(void) { return 0; }\n")
        (source / "CMakeLists.txt").write_text(
            'cmake_minimum_required(VERSION 3.20)\nproject(llvm_stage C)\n'
            'add_library(llvm-stage STATIC stage.c)\n'
            'install(TARGETS llvm-stage DESTINATION lib)\n')
        for generator, tool in (("Unix Makefiles", "gmake"), ("Ninja", "ninja")):
            prefix = work / ("stage-" + tool)
            subprocess.run([tools / "cmake", "--fresh", "-S", source, "-B", build,
                            "-G", generator, "-DCMAKE_MAKE_PROGRAM=" + str(tools / tool),
                            "-DCMAKE_C_COMPILER=" + str(tools / "clang"),
                            "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY",
                            "-DCMAKE_AR=" + str(tools / "llvm-ar"),
                            "-DCMAKE_RANLIB=" + str(tools / "llvm-ranlib"),
                            "-DCMAKE_STRIP=" + str(tools / "llvm-strip"),
                            "-DCMAKE_INSTALL_PREFIX=" + str(prefix)], check=True, env=env)
            query(generator)
            subprocess.run([tools / "cmake", "--build", build, "--target", install],
                           check=True, env=env)
            assert (prefix / "lib/libllvm-stage.a").is_file()
            # An interrupted configuration can leave only the generator in its cache.
            for marker in ("Makefile", "build.ninja"):
                (build / marker).unlink(missing_ok=True)
            query(generator)
        (build / "CMakeCache.txt").write_text("# Interrupted before generator selection\n")
        query("Ninja")


if __name__ == "__main__":
    main()
