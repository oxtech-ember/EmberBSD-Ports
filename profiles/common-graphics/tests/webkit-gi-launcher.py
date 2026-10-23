#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the actual WebKit GI consumer.
"""Check pkgsrc configure environments and the release FindGI module without SSH."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tarfile



def check_gir_commands(run, cmake, module, work, tools, target_gir, wrapper, env):
    """Inspect real CMake commands. The imported library is never built or run."""
    work.mkdir()
    project = work / "project"
    project.mkdir()
    header = project / "include-probe.h"
    header.write_text("typedef unsigned IncludeProbeToken;\n")
    (project / "CMakeLists.txt").write_text(
        'cmake_minimum_required(VERSION 3.20)\nproject(GIRIncludeCommands NONE)\n'
        'set(ENABLE_INTROSPECTION ON)\ninclude("' + str(module) + '")\n'
        'add_library(IncludeProbe SHARED IMPORTED)\n'
        'set_target_properties(IncludeProbe PROPERTIES IMPORTED_LOCATION '
        '"${CMAKE_BINARY_DIR}/libIncludeProbe.so")\n'
        'GI_INTROSPECT(IncludeProbe 1.0 include-probe.h NO_IMPLICIT_SOURCES '
        'SOURCES "' + str(header) + '" DEPENDENCIES Gtk-3.0:gtk+-3.0)\n')
    common = [cmake, "-G", "Ninja", "-S", project,
              "-DCMAKE_MAKE_PROGRAM=" + str(tools / "bin/ninja"),
              "-DPKG_CONFIG_EXECUTABLE=" + str(tools / "bin/pkg-config"),
              "-DGI_SCANNER_EXE=" + str(tools / "bin/g-ir-scanner"),
              "-DGI_COMPILER_EXE=" + str(tools / "bin/g-ir-compiler")]
    for mode in ("cross", "native"):
        build = work / mode
        argv = [*common, "-B", build]
        if mode == "cross":
            argv += ["-DCMAKE_SYSTEM_NAME=NetBSD", "-DGI_LDD_WRAPPER=" + str(wrapper),
                     "-DGI_TARGET_GIR_DIR=" + str(target_gir)]
        result = run("gir-commands-" + mode, argv, env)
        assert result.returncode == 0, result.stderr
        ninja = (build / "build.ninja").read_text()
        scanner = next(line for line in ninja.splitlines()
                       if "COMMAND =" in line and "--namespace=IncludeProbe" in line)
        compiler = next(line for line in ninja.splitlines()
                        if "COMMAND =" in line and "--output=" in line
                        and "g-ir-compiler" in line)
        assert "--warn-all --warn-error" in scanner
        if mode == "cross":
            assert "--add-include-path=" + str(target_gir) in scanner
            target_flag = "--includedir=" + str(target_gir)
            local_flag = "--includedir=" + str(build)
            assert target_flag in compiler and compiler.index(local_flag) < compiler.index(target_flag)
        else:
            assert "--add-include-path=" not in scanner
            assert str(target_gir) not in compiler
    for name, value in (("missing", ""), ("relative", "share/gir-1.0"),
                        ("absent", str(work / "absent-gir"))):
        rejected = run("gir-directory-" + name, [*common, "-B", work / name,
            "-DCMAKE_SYSTEM_NAME=NetBSD", "-DGI_LDD_WRAPPER=" + str(wrapper),
            "-DGI_TARGET_GIR_DIR=" + value], env)
        assert rejected.returncode != 0 and "GI_TARGET_GIR_DIR" in rejected.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["pkgsrc", "makeconf", "bmake", "cmake", "archive", "python", "work"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    for name, value in vars(args).items():
        setattr(args, name, value.resolve())
    args.work.mkdir(parents=True, exist_ok=False)
    for name in ["build", "cache", "source", "project"]:
        (args.work / name).mkdir()
    commands = []

    def run(name, command, env=None):
        command = [str(v) for v in command]
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=180)
        (args.work / (name + ".log")).write_text(result.stdout + result.stderr)
        commands.append({"name": name, "argv": command, "exit": result.returncode})
        (args.work / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        return result

    recipe = args.pkgsrc / "www/webkit-gtk41"
    data = args.archive.read_bytes()
    distinfo = (recipe / "distinfo").read_text()
    for name, value in [("SHA512", hashlib.sha512(data).hexdigest()),
                        ("BLAKE2s", hashlib.blake2s(data).hexdigest()), ("Size", str(len(data)))]:
        assert re.search(r"^" + name + r" \(webkitgtk-2\.54\.1\.tar\.xz\) = " + value + r"(?: bytes)?$",
                         distinfo, re.M), "Archive differs from recipe distinfo"
    source = args.work / "source/Source/cmake/FindGI.cmake"
    source.parent.mkdir(parents=True)
    with tarfile.open(args.archive) as archive:
        source.write_bytes(archive.extractfile("webkitgtk-2.54.1/Source/cmake/FindGI.cmake").read())
    patch = recipe / "patches/patch-Source_cmake_FindGI.cmake"
    applied = subprocess.run(["patch", "-f", "-p0", "-F", "0", "-d", str(args.work / "source")],
                             input=patch.read_text(), capture_output=True, text=True)
    (args.work / "patch.log").write_text(applied.stdout + applied.stderr)
    assert applied.returncode == 0, "Release FindGI patch failed"
    keys = ["CONFIGURE_ENV", "MAKE_ENV", "TOOLBASE", "CROSS_DESTDIR", "TOOLDIR",
            "MACHINE_GNU_PLATFORM", "_WEBKIT_BUILD_RUBY", "PKG_FAIL_REASON", "CROSS_LOCALBASE",
            "CMAKE_CONFIGURE_ARGS"]
    results = {}
    for api in ["41", "60"]:
        config = args.work / ("query-" + api + ".json")
        config.write_text("{}\n")
        base = [args.bmake, "-C", args.pkgsrc / ("www/webkit-gtk" + api),
                "MAKECONF=" + str(args.makeconf), "WRKOBJDIR=" + str(args.work / "objects"),
                "EMBERBSD_CROSS_BUILD_PYTHON=" + str(args.python),
                "EMBERBSD_GI_PYTHON=" + str(args.python), "EMBERBSD_GI_QUERY_CONFIG=" + str(config),
                "EMBERBSD_CROSS_BUILD_CC=/usr/bin/cc"]
        query = run("metadata-" + api, [*base, *[v for key in keys for v in ["-v", key]]])
        assert query.returncode == 0, query.stderr
        values = dict(zip(keys, query.stdout.splitlines(), strict=True))
        (args.work / ("metadata-" + api + ".json")).write_text(json.dumps(values, indent=2) + "\n")
        results[api] = values
        assert not values["PKG_FAIL_REASON"], values["PKG_FAIL_REASON"]
        config.write_text(json.dumps({"build_root": str(args.work / "build"),
            "cache": str(args.work / "cache"), "sysroot": values["CROSS_DESTDIR"],
            "readelf": values["TOOLDIR"] + "/bin/" + values["MACHINE_GNU_PLATFORM"] + "-readelf",
            "ssh": "unused.invalid"}, indent=2) + "\n")
        environment = dict(os.environ)
        environment.update(item.split("=", 1) for item in shlex.split(values["CONFIGURE_ENV"]))
        # FindGI uses native scanner metadata in this bounded configure probe.
        environment.update(PKG_CONFIG_SYSROOT_DIR="", PKG_CONFIG_PATH="",
            PKG_CONFIG_LIBDIR=values["TOOLBASE"] + "/lib/pkgconfig:" + values["TOOLBASE"] + "/share/pkgconfig",
            TEST_WORK=str(args.work / "build"), TEST_SYSROOT=values["CROSS_DESTDIR"],
            TEST_READELF=json.loads(config.read_text())["readelf"])
        project = args.work / "project/CMakeLists.txt"
        project.write_text('cmake_minimum_required(VERSION 3.20)\nproject(WebKitGIConsumer NONE)\n'
            'set(ENABLE_INTROSPECTION ON)\ninclude("' + str(source) + '")\n'
            'separate_arguments(query UNIX_COMMAND "$ENV{GI_CROSS_LAUNCHER}")\n'
            'execute_process(COMMAND ${query} --check "$ENV{TEST_WORK}" "$ENV{TEST_SYSROOT}" '
            '"$ENV{TEST_READELF}" aarch64 RESULT_VARIABLE status OUTPUT_VARIABLE output ERROR_VARIABLE error)\n'
            'if(NOT "${status}" STREQUAL "0")\n'
            '  message(FATAL_ERROR "GI query preflight failed: ${status}: ${output}${error}")\nendif()\n'
            'message(STATUS "${output}")\n')
        command = [args.cmake, "-S", args.work / "project", "-B", args.work / ("cmake-" + api),
            "-DCMAKE_SYSTEM_NAME=NetBSD", "-DCMAKE_SYSTEM_PROCESSOR=aarch64",
            "-DGI_LDD_WRAPPER=" + str(args.pkgsrc / "devel/gobject-introspection/files/elf-needed.sh"),
            "-DPKG_CONFIG_EXECUTABLE=" + values["TOOLBASE"] + "/bin/pkg-config",
            "-DGI_SCANNER_EXE=" + values["TOOLBASE"] + "/bin/g-ir-scanner",
            "-DGI_COMPILER_EXE=" + values["TOOLBASE"] + "/bin/g-ir-compiler",
            "-DGI_TARGET_GIR_DIR=" + values["CROSS_DESTDIR"] + values["CROSS_LOCALBASE"] + "/share/gir-1.0"]
        checked = run("configure-" + api, command, environment)
        assert checked.returncode == 0, "Actual FindGI/configure launcher failed; see configure log"
        assert "PASS: GI query configuration matches" in checked.stdout
        target_gir = Path(values["CROSS_DESTDIR"] + values["CROSS_LOCALBASE"]) / "share/gir-1.0"
        assert "-DGI_TARGET_GIR_DIR:PATH=" + str(target_gir) in values["CMAKE_CONFIGURE_ARGS"]
        if api == "41":
            check_gir_commands(run, args.cmake, source, args.work / "gir-commands",
                               Path(values["TOOLBASE"]), target_gir,
                               args.pkgsrc / "devel/gobject-introspection/files/elf-needed.sh",
                               environment)
        launcher = shlex.split(environment["GI_CROSS_LAUNCHER"])
        assert len(launcher) == 4 and Path(launcher[0]).resolve() == args.python
        assert launcher[1:3] == ["-E", "-S"]
        assert launcher[3].endswith("/target-query.py") and Path(launcher[3]).is_file()
        assert "target-query.rb" not in values["CONFIGURE_ENV"] + values["MAKE_ENV"]
        native = run("native-" + api, [*base, "USE_CROSS_COMPILE=no", "-v", "CONFIGURE_ENV",
                                              "-v", "CMAKE_CONFIGURE_ARGS"])
        assert native.returncode == 0 and "GI_CROSS_LAUNCHER=" not in native.stdout
        assert "GI_TARGET_GIR_DIR" not in native.stdout
        negative = list(command)
        negative[4] = args.work / ("missing-" + api)
        refused = run("missing-launcher-" + api, negative,
                      environment | {"GI_CROSS_LAUNCHER": ""})
        assert refused.returncode != 0 and "Cross introspection requires a real GI_CROSS_LAUNCHER" in refused.stderr
    inputs = [Path(__file__).resolve(), args.makeconf, args.archive, recipe / "cross.mk", patch,
              args.pkgsrc / "devel/gobject-introspection/cross.mk",
              args.pkgsrc / "devel/gobject-introspection/files/target-query.py"]
    (args.work / "result.json").write_text(json.dumps({"scope": "Real bmake and release FindGI configure/preflight for API 4.1 and 6.0. No WebKit build, SSH or target execution.",
        "inputs": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        "commands": commands}, indent=2) + "\n")
    print("PASS: both WebKit APIs configure with the real Python GI launcher; native and refusal boundaries retained")


if __name__ == "__main__":
    main()
