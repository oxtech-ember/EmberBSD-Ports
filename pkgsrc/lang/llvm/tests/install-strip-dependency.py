#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Verify LLVM's staged CMake install behavior.
"""Prove pkgsrc bmake install/strip keeps staging actions without rerunning ALL.

Use the selected native SDK CMake, BSD/GNU make, compiler, Python, and shell.
The baseline case demonstrates CMake's default second ALL traversal. The
fixed case checks that the LLVM configure option skips only that traversal;
install(CODE), strip, and the installed executable remain required.
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess


def require(value, message):
    if not value:
        raise AssertionError(message)


def run(argv, env, cwd):
    result = subprocess.run(argv, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=120)
    require(result.returncode == 0,
            f"command failed ({result.returncode}): {argv!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cmake", "make", "bmake", "compiler", "strip", "python", "shell", "work"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    tools = (args.cmake, args.make, args.bmake, args.compiler, args.strip,
             args.python, args.shell)
    require(all(path.is_absolute() and path.is_file() and os.access(path, os.X_OK)
                for path in tools), "Every selected tool must be an executable absolute path")
    work = args.work
    require(work.is_absolute() and work.resolve() == work and not os.path.lexists(work),
            "Use a fresh absolute work directory")
    work.mkdir(mode=0o700)
    source = work / "source"
    source.mkdir()
    (source / "main.c").write_text("int main(void) { return 0; }\n")
    (source / "count-all.py").write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "path = Path(sys.argv[1])\n"
        "with path.open('a') as stream: stream.write('all\\n')\n")
    (source / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.20)\n"
        "project(InstallStripDependencyProof C)\n"
        "add_executable(installed-app main.c)\n"
        "install(TARGETS installed-app RUNTIME DESTINATION bin)\n"
        "install(CODE [[\n"
        "if(NOT CMAKE_INSTALL_DO_STRIP)\n"
        "  message(FATAL_ERROR \"install/strip lost CMAKE_INSTALL_DO_STRIP\")\n"
        "endif()\n"
        "file(WRITE \"${CMAKE_INSTALL_PREFIX}/install-code.txt\" \"strip-enabled\\n\")\n"
        "]])\n"
        "add_custom_target(count_all ALL\n"
        "  COMMAND \"${Python3_EXECUTABLE}\" \"${CMAKE_SOURCE_DIR}/count-all.py\" \"${CMAKE_BINARY_DIR}/all-count\")\n")

    strip_log = work / "strip.log"
    strip_wrapper = work / "selected-strip"
    strip_wrapper.write_text(
        f"#!{args.shell}\n"
        f"echo invoked >> {shlex.quote(str(strip_log))}\n"
        f"exec {shlex.quote(str(args.strip))} \"$@\"\n")
    strip_wrapper.chmod(0o755)
    shell_log = work / "shell.log"
    shell_wrapper = work / "selected-shell"
    shell_wrapper.write_text(
        f"#!{args.shell}\n"
        f"echo invoked >> {shlex.quote(str(shell_log))}\n"
        f"exec {shlex.quote(str(args.shell))} \"$@\"\n")
    shell_wrapper.chmod(0o755)
    env = dict(os.environ)
    env.update(PATH=str(args.cmake.parent), SHELL=str(shell_wrapper), TMPDIR=str(work),
               LC_ALL="C", TZ="UTC")
    env.pop("CMAKE_PREFIX_PATH", None)
    env.pop("CMAKE_FIND_ROOT_PATH", None)

    counts = {}
    for name, skip in (("baseline", False), ("skip-all", True)):
        build = work / name
        prefix = work / (name + "-prefix")
        configure = [str(args.cmake), "-S", str(source), "-B", str(build),
                     "-G", "Unix Makefiles", "-DCMAKE_MAKE_PROGRAM=" + str(args.make),
                     "-DCMAKE_C_COMPILER=" + str(args.compiler),
                     "-DCMAKE_STRIP=" + str(strip_wrapper),
                     "-DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld",
                     "-DPython3_EXECUTABLE=" + str(args.python),
                     "-DCMAKE_INSTALL_PREFIX=" + str(prefix)]
        if skip:
            configure.append("-DCMAKE_SKIP_INSTALL_ALL_DEPENDENCY=ON")
        run(configure, env, work)
        generated_makefile = (build / "Makefile").read_text()
        require(f"SHELL = {args.shell}" in generated_makefile,
                name + " did not configure CMake with the selected SDK shell")
        phases = work / (name + ".mk")
        phases.write_text(
            f"CMAKE= {args.cmake}\nBUILD= {build}\nSHELL= {shell_wrapper}\n"
            ".PHONY: all install/strip\n"
            "all:\n\t${CMAKE} --build ${BUILD} --target all -- SHELL=${SHELL}\n"
            "install/strip:\n\t${CMAKE} --build ${BUILD} --target install/strip -- SHELL=${SHELL}\n")
        run([str(args.bmake), "-f", str(phases), "SHELL=" + str(shell_wrapper), "all"], env, work)
        counts[name + "_after_build"] = (build / "all-count").read_text().splitlines()
        strip_calls_before = (len(strip_log.read_text().splitlines())
                              if strip_log.exists() else 0)
        run([str(args.bmake), "-f", str(phases), "SHELL=" + str(shell_wrapper),
             "install/strip"], env, work)
        counts[name + "_after_install"] = (build / "all-count").read_text().splitlines()
        strip_calls_after = len(strip_log.read_text().splitlines())
        require((prefix / "bin/installed-app").is_file(), name + " did not stage the program")
        require((prefix / "install-code.txt").read_text() == "strip-enabled\n",
                name + " skipped install(CODE) or lost the strip mode")
        require(strip_calls_after > strip_calls_before,
                name + " did not invoke the selected strip program")

    require(counts["baseline_after_build"] == ["all"] and
            counts["baseline_after_install"] == ["all", "all"],
            "Baseline did not reproduce install/strip's second ALL traversal")
    require(counts["skip-all_after_build"] == ["all"] and
            counts["skip-all_after_install"] == ["all"],
            "Skip option did not remove only the install dependency on ALL")
    require(shell_log.is_file() and shell_log.read_text().splitlines(),
            "The selected SDK shell wrapper was not used")
    print("PASS: baseline repeated ALL; skip option preserved install/strip actions")


if __name__ == "__main__":
    main()
