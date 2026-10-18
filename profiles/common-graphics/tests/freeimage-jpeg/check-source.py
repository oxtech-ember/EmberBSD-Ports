#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), paired real-source JPEG regression.
"""Run with [--target] ARCHIVE GCC16_GXX JPEG_PREFIX NEW_WORK. Use Python's standard library."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

PIN = "dab013044c3d9122b0a93cee7b53a656426bccc571d3d46880dd8d90a10d1968"
target_mode = len(sys.argv) > 1 and sys.argv[1] == "--target"
if target_mode:
    sys.argv.pop(1)
if len(sys.argv) != 5:
    raise SystemExit(__doc__)
archive, compiler, provider = (Path(p).resolve(strict=True) for p in sys.argv[1:4])
work = Path(sys.argv[4])
if not work.is_absolute() or work.exists() or work.is_symlink():
    raise SystemExit("Use a new absolute work directory.")
if hashlib.file_digest(archive.open("rb"), "sha256").hexdigest() != PIN:
    raise SystemExit("The official archive hash differs.")
work.mkdir()
commands = []


def run(label, args, expected=0, **kwargs):
    args = [str(a) for a in args]
    completed = subprocess.run(args, capture_output=True, **kwargs)
    (work / (label + ".stdout")).write_bytes(completed.stdout)
    (work / (label + ".stderr")).write_bytes(completed.stderr)
    commands.append({"label": label, "args": args, "status": completed.returncode})
    (work / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    if expected is not None and completed.returncode != expected:
        raise SystemExit(f"Unexpected status for {label}: {completed.returncode}. See {work}.")
    return completed.stdout.decode(errors="replace") + completed.stderr.decode(errors="replace")


if not run("compiler", [compiler, "-dumpfullversion"]).startswith("16."):
    raise SystemExit("GCC16 is required.")
triplet = run("triplet", [compiler, "-dumpmachine"]).lower().strip()
if target_mode != ("netbsd" in triplet):
    raise SystemExit("Select native Linux or --target NetBSD GCC16 consistently.")
if not target_mode:
    run("valgrind-version", ["valgrind", "--version"])
    run("cppcheck-version", ["cppcheck", "--version"])
    clang = shutil.which("clang++-19")
    if not clang:
        raise SystemExit("Clang19 is required for analysis only.")
    run("clang-version", [clang, "--version"])
provider_env = dict(os.environ, PKG_CONFIG_LIBDIR=str(provider / "lib/pkgconfig"))
version = run("provider-version", ["pkg-config", "--modversion", "libturbojpeg"], env=provider_env).strip()
if version != "3.2.0":
    raise SystemExit("The common libjpeg-turbo 3.2.0 provider is required.")
inputs = [archive, compiler, Path(__file__).resolve()]
for name in ("libjpeg.so", "libturbojpeg.so"):
    library = (provider / "lib" / name).resolve(strict=True)
    proof = run(name + "-compiler", ["readelf", "-p", ".comment", library])
    if not re.search(r"GCC:.*\b16\.", proof):
        raise SystemExit("The native provider lacks GCC16 provenance: " + name)
    inputs.append(library)
fixture = Path(__file__).with_name("contract.cpp").resolve()
patches = Path(__file__).resolve().parents[2] / "recipes/graphics/freeimage/patches"
patch = patches / "patch-Source_FreeImageToolkit_JPEGTransform.cpp"
inputs += [fixture, patch, patches / "patch-CMakeLists.txt"]
members = ["Source/FreeImage.h", "Source/Utilities.h", "Source/FreeImageIO.h",
           "Source/FreeImageToolkit/JPEGTransform.cpp", "CMakeLists.txt"]
sources = {}
analysis = {}
if target_mode:
    sysroot = Path(run("sysroot", [compiler, "-print-sysroot"]).strip()).resolve(strict=True)
    runtime_path = "/" + provider.relative_to(sysroot).as_posix() + "/lib"
else:
    runtime_path = str(provider / "lib")
    search = run("compiler-search", [compiler, "-E", "-x", "c++", "-v", "/dev/null"])
    include_section = search.split('#include <...> search starts here:\n', 1)[1].split("End of search list.", 1)[0]
    cxx_headers = [line.strip() for line in include_section.splitlines() if "/c++/" in line]
    if not cxx_headers:
        raise SystemExit("Could not find the selected GCC16 C++ headers.")
for variant in ("before", "after"):
    source = work / variant
    source.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        for name in members:
            member = tar.getmember("FreeImage-3.19.25/" + name)
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
    if variant == "after":
        run("apply-jpeg", ["patch", "-d", source, "-p0", "--fuzz=0", "-i", patch])
        run("apply-cmake", ["patch", "-d", source, "-p0", "--fuzz=0", "-i", patches / "patch-CMakeLists.txt"])
    unit = source / "Source/FreeImageToolkit/JPEGTransform.cpp"
    sources[variant] = hashlib.file_digest(unit.open("rb"), "sha256").hexdigest()
    flags = ["-std=c++17", "-O2", "-g", "-Wall", "-Wextra", "-DFREEIMAGE_SYSTEM_LIBJPEG",
             "-I" + str(provider / "include"), "-I" + str(source / "Source")]
    binary = source / "contract"
    link = ["-L" + str(provider / "lib"), "-Wl,-rpath," + runtime_path,
            "-Wl,--gc-sections", "-Wl,--wrap=_Znwm", "-ljpeg", "-lturbojpeg"]
    if target_mode:
        link += ["-Wl,-rpath,/usr/pkg/gcc16/lib"]
    run(variant + "-compile", [compiler, *flags, "-ffunction-sections", "-fdata-sections", unit, fixture, *link, "-o", binary])
    if target_mode:
        run(variant + "-elf", ["readelf", "-h", binary])
        sources[variant + "_binary"] = hashlib.file_digest(binary.open("rb"), "sha256").hexdigest()
        continue
    outcome = run(variant + "-run", [binary], expected=1 if variant == "before" else 0)
    if variant == "before":
        if "FAIL: valid perfect vertical transform: Lossless JPEG transforms are unavailable" not in outcome:
            raise SystemExit("The baseline did not reproduce the intended failure.")
    elif "PASS: 334 transform/crop/error cases" not in outcome:
        raise SystemExit("The repaired coefficient/error oracle did not finish.")
    if variant == "after":
        memory = run("memcheck", ["valgrind", "--error-exitcode=97", "--leak-check=full",
                     "--show-leak-kinds=all", "--errors-for-leak-kinds=all", "--track-origins=yes", binary])
        if "in use at exit: 0 bytes in 0 blocks" not in memory or "ERROR SUMMARY: 0 errors from 0 contexts (suppressed: 0 from 0)" not in memory:
            raise SystemExit("The strict memory result differs.")
    preprocessed = source / "transform.ii"
    run(variant + "-preprocess", [compiler, *flags, "-E", unit, "-o", preprocessed])
    # Preserve actual-GCC-header coverage and any analyzer parser limitations.
    run(variant + "-cppcheck-preprocessed", ["cppcheck", "--enable=all", "--inconclusive",
        "--check-level=exhaustive", "--language=c++", "--std=c++17", "--platform=unix64",
        "--xml", "--xml-version=2", preprocessed])
    # Cppcheck recommends modeled system headers. Keep the real codec headers,
    # selected macro, language, and native platform for this additional pass.
    run(variant + "-cppcheck-source", ["cppcheck", "--enable=all", "--inconclusive",
        "--check-level=exhaustive", "--language=c++", "--std=c++17", "--platform=unix64",
        "--xml", "--xml-version=2", "-DFREEIMAGE_SYSTEM_LIBJPEG", "-I" + str(provider / "include"),
        "-I" + str(source / "Source"), unit])
    def findings(label):
        root = ET.fromstring((work / (label + ".stderr")).read_bytes())
        return [{"id": e.get("id"), "severity": e.get("severity"), "message": e.get("msg")}
                for e in root.findall("errors/error")]
    analysis[variant] = {"preprocessed": findings(variant + "-cppcheck-preprocessed"),
                         "modeled_system_headers": findings(variant + "-cppcheck-source")}
    clang_flags = ["-std=c++17", "-DFREEIMAGE_SYSTEM_LIBJPEG", "-nostdinc++"]
    for header in cxx_headers:
        clang_flags += ["-isystem", header]
    diagnostics = run(variant + "-clang-analyze", [clang, "--analyze", "-Xanalyzer", "-analyzer-output=text",
        *clang_flags, "-I" + str(provider / "include"), "-I" + str(source / "Source"), unit,
        "-o", source / "analysis.plist"])
    analysis[variant]["clang_diagnostics"] = diagnostics
    if diagnostics:
        raise SystemExit("Review Clang analyzer diagnostics before acceptance.")
    if variant == "after":
        # Compile/link the actual patched system-JPEG CMake branch. Other
        # FreeImage codec packages and the full TestAPI suite are separate gates.
        cmake_source = source / "cmake-contract"
        cmake_source.mkdir()
        text = (source / "CMakeLists.txt").read_text()
        branch = text[text.index("if(BUILD_LIBJPEG)\n"):text.index("if(BUILD_LIBOPENJPEG)\n")]
        (cmake_source / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.16)\nproject(JPEGContract LANGUAGES C CXX)\n"
            "set(BUILD_LIBJPEG ON)\nset(USE_SYSTEM_LIBJPEG ON)\n" + branch +
            f'\nadd_executable(contract "{unit}" "{fixture}")\n'
            f'target_include_directories(contract PRIVATE "{source / "Source"}")\n'
            "target_compile_features(contract PRIVATE cxx_std_17)\n"
            "target_compile_options(contract PRIVATE -UNDEBUG -ffunction-sections -fdata-sections)\n"
            'target_link_options(contract PRIVATE "-Wl,--gc-sections" "-Wl,--wrap=_Znwm")\n'
            "target_link_libraries(contract PRIVATE ${FreeImage_LIBS})\n")
        build = source / "cmake-build"
        c_compiler = run("c-compiler", [compiler, "-print-prog-name=gcc"]).strip()
        if not Path(c_compiler).is_absolute():
            c_compiler = shutil.which(c_compiler)
        if not c_compiler or not run("c-compiler-version", [c_compiler, "-dumpfullversion"]).startswith("16."):
            raise SystemExit("CMake also requires native GCC16 for C.")
        run("cmake-configure", ["cmake", "-S", cmake_source, "-B", build,
            "-DCMAKE_C_COMPILER=" + c_compiler, "-DCMAKE_CXX_COMPILER=" + str(compiler),
            "-DCMAKE_PREFIX_PATH=" + str(provider), "-DCMAKE_BUILD_TYPE=Release"], env=provider_env)
        run("cmake-build", ["cmake", "--build", build, "--parallel", "2"])
        run("cmake-run", [build / "contract"])
result = {"status": "BUILT_UNRUN" if target_mode else "PASS", "scope": "Real upstream JPEGTransform.cpp. Target mode builds paired executables without running them. Native mode runs the public API coefficient/marker/error oracle. Full package acceptance remains separate.",
          "sources": sources, "analysis": analysis,
          "input_sha256": {str(p): hashlib.file_digest(p.open("rb"), "sha256").hexdigest() for p in inputs}}
(work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print("BUILT_UNRUN: paired target executables; run before/contract (expect 1) and after/contract (expect 0) on EmberBSD." if target_mode else
      "PASS: genuine unsupported-transform baseline, 334 repaired cases, strict Memcheck, paired static analysis and patched CMake linkage.")
