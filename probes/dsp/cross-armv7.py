#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors
"""Stage the common FFTW and liquid-dsp profiles for EmberBSD earmv7hf."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile


TARGET = "armv7--netbsdelf-eabihf"
VERSION = "16.2.0"
PATCH_SHA256 = "319226bf9468366108a1762cc74c321522bda5170bd77c74bd62e5294f3bd151"
PROBES = Path(__file__).resolve().parent.parent


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def path_arg(value):
    path = Path(value)
    # Autoconf, Libtool and generated CMake files also interpret these paths.
    if not path.is_absolute() or not re.fullmatch(r"[A-Za-z0-9_./+-]+", value):
        raise argparse.ArgumentTypeError("Use an absolute path without shell metacharacters or spaces.")
    return path


def positive(value):
    if not re.fullmatch(r"[0-9]+", str(value)) or int(value) < 1:
        raise argparse.ArgumentTypeError("The job count must be positive.")
    return int(value)


def output(command):
    return subprocess.check_output([str(arg) for arg in command], text=True).strip()


def validate(compiler, sysroot, work):
    for path in (compiler.resolve(), sysroot.resolve(), work.parent.resolve() / work.name):
        path_arg(str(path))
    if work.exists() or work.is_symlink():
        raise ValueError("Work path already exists; choose an unused directory.")
    cc = compiler / "bin" / (TARGET + "-gcc")
    if output([cc, "-dumpfullversion"]) != VERSION:
        raise ValueError("This profile requires GCC " + VERSION)
    if output([cc, "-dumpmachine"]) != TARGET:
        raise ValueError("The compiler must target " + TARGET)
    macros = subprocess.check_output(
        [str(cc), "-dM", "-E", "-x", "c", "-"], input="", text=True)
    if "__clang__" in macros or "#define __GNUC__ 16" not in macros:
        raise ValueError("Use the GCC16 compiler, not a Clang compatibility driver.")
    for tool in ("ar", "ranlib", "readelf", "nm"):
        if not os.access(compiler / "bin" / (TARGET + "-" + tool), os.X_OK):
            raise ValueError("Missing target tool: " + tool)
    for name in ("usr/include/sys/param.h", "usr/lib/libc.so"):
        if not (sysroot / name).is_file():
            raise ValueError("Missing EmberBSD sysroot input: " + name)
    elf = output([compiler / "bin" / (TARGET + "-readelf"), "-h", sysroot / "usr/lib/libc.so"])
    if not re.search(r"Machine:\s+ARM\b", elf) or "hard-float ABI" not in elf:
        raise ValueError("The sysroot libc must be an ARM ELF hard-float library.")
    return cc


def verify_archive(archive, expected):
    if digest(archive) != expected:
        raise ValueError("Archive checksum mismatch: " + archive.name)
    # Pinned archives are still checked before an external tar extracts them.
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                raise ValueError("Unsafe archive member: " + member.name)
            if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise ValueError("Unsupported archive member: " + member.name)


def build(args):
    compiler = args.compiler.resolve()
    sysroot = args.sysroot.resolve()
    work = args.work
    cc = validate(compiler, sysroot, work)
    for tool in (args.make, "cmake", "tar", "patch") + (() if args.source_cache else ("curl",)):
        if shutil.which(tool) is None:
            raise ValueError("Missing host tool: " + tool)
    patch = PROBES / "liquid-dsp/patches/cmake-fftw-selection.patch"
    if digest(patch) != PATCH_SHA256:
        raise ValueError("The FFTW patch changed; review this profile before rebuilding.")
    work.mkdir()  # Fail if another process claimed the same output directory.
    work = work.resolve()
    for directory in ("src", "archives", "logs", "stage/usr/pkg"):
        (work / directory).mkdir(parents=True)
    prefix = work / "stage/usr/pkg"
    env = os.environ.copy()

    def run(name, command, cwd=None, stdin=None, extra_env=None, failure=None):
        print(name, flush=True)
        log = work / "logs" / (name + ".log")
        with log.open("w") as stream:
            result = subprocess.run([str(arg) for arg in command], cwd=cwd,
                                    env=env | (extra_env or {}), stdin=stdin,
                                    stdout=stream, stderr=subprocess.STDOUT)
        if failure is not None:
            if result.returncode == 0 or failure not in log.read_text(errors="replace"):
                raise RuntimeError("Expected causal failure was absent: " + name)
        elif result.returncode:
            print("\n".join(log.read_text(errors="replace").splitlines()[-60:]), file=sys.stderr)
            raise RuntimeError("Build step failed: " + name)

    sources = []
    for component in ("fftw", "liquid-dsp"):
        for line in (PROBES / component / "sources.tsv").read_text().splitlines():
            name, expected, url = line.split()
            archive = work / "archives" / name
            if args.source_cache:
                shutil.copyfile(args.source_cache / name, archive)
            else:
                run(component + "-fetch", ["curl", "-fLsS", "--connect-timeout", "20",
                    "--max-time", "900", url, "-o", archive])
            verify_archive(archive, expected)
            run(component + "-extract", ["tar", "-xf", archive, "-C", work / "src"])
            sources.append({"archive": name, "sha256": expected, "url": url})

    wrapper = work / "cc"
    # Use AAPCS frames. The GCC16 ARM APCS sibling-call path can corrupt r12
    # while restoring VFP state. The real n=75 FFT consumer covers that path.
    wrapper.write_text(f'#!/bin/sh\nexec "{cc}" --sysroot="{sysroot}" '
                       f'-isystem "{sysroot}/usr/include" -mno-apcs-frame "$@"\n')
    wrapper.chmod(0o755)
    env.update(CC=str(wrapper), AR=str(compiler / "bin" / (TARGET + "-ar")),
               RANLIB=str(compiler / "bin" / (TARGET + "-ranlib")),
               CFLAGS="-O2 -g -gdwarf-4", LDFLAGS="-Wl,-rpath,/usr/pkg/lib",
               PKG_CONFIG_LIBDIR=str(prefix / "lib/pkgconfig"),
               PKG_CONFIG_SYSROOT_DIR=str(work / "stage"))
    fftw = work / "src/fftw-3.3.11"
    host = output(["sh", fftw / "config.guess"])
    for precision in ("double", "float"):
        directory = work / ("fftw-" + precision)
        directory.mkdir()
        options = ["--enable-float"] if precision == "float" else []
        run(precision + "-configure", [fftw / "configure", "--host=" + TARGET,
            "--build=" + host, "--prefix=/usr/pkg", "--enable-shared", "--disable-static",
            "--enable-threads", "--disable-fortran", "--disable-doc"] + options, cwd=directory)
        run(precision + "-build", [args.make, "-j", args.jobs], cwd=directory)
        run(precision + "-install", [args.make, "DESTDIR=" + str(work / "stage"), "install"], cwd=directory)

    toolchain = work / "toolchain.cmake"
    toolchain.write_text(f'''set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR armv7)
set(CMAKE_C_COMPILER "{wrapper}")
set(CMAKE_AR "{env['AR']}")
set(CMAKE_RANLIB "{env['RANLIB']}")
set(CMAKE_SYSROOT "{sysroot}")
set(CMAKE_FIND_ROOT_PATH "{sysroot}" "{work / 'stage'}")
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
''')
    liquid = work / "src/liquid-dsp-1.8.3"

    def configure(directory):
        return ["cmake", "-S", liquid, "-B", directory,
            "-DCMAKE_TOOLCHAIN_FILE=" + str(toolchain), "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-DCMAKE_INSTALL_PREFIX=/usr/pkg",
            "-DCMAKE_INSTALL_LIBDIR=lib", "-DBUILD_SHARED_LIBS=ON", "-DBUILD_STATIC_LIBS=OFF",
            "-DBUILD_EXAMPLES=OFF", "-DBUILD_AUTOTESTS=OFF", "-DBUILD_BENCHMARKS=OFF",
            "-DBUILD_SANDBOX=OFF", "-DBUILD_DOC=OFF", "-DENABLE_TIMESTAMPS=OFF",
            "-DENABLE_SIMD=OFF", "-DFIND_SIMD=OFF", "-DFIND_FFTW=ON",
            "-DCMAKE_REQUIRE_FIND_PACKAGE_fftw3f=ON", "-Dfftw3f_INCLUDE_DIR=" + str(prefix / "include"),
            "-Dfftw3f_LIBRARY=" + str(prefix / "lib/libfftw3f.so"), "-DCMAKE_INSTALL_RPATH=/usr/pkg/lib"]

    baseline = work / "liquid-baseline"
    patched = work / "liquid-build"
    backend = PROBES / "liquid-dsp/tests/backend-selection.c"
    run("liquid-baseline-configure", configure(baseline))
    run("baseline-backend", [wrapper, "-std=c11", "-I" + str(liquid / "include"),
        "-I" + str(baseline), "-I" + str(prefix / "include"), "-c", backend,
        "-o", work / "baseline.o"], failure="FFTW_BACKEND_REQUIRED")
    with patch.open() as stream:
        run("liquid-patch", ["patch", "-d", liquid, "-p1"], stdin=stream)
    run("liquid-configure", configure(patched))
    run("liquid-build", ["cmake", "--build", patched, "--parallel", args.jobs])
    run("liquid-install", ["cmake", "--install", patched], extra_env={"DESTDIR": str(work / "stage")})
    tests = prefix / "libexec/ember-dsp"
    tests.mkdir(parents=True)
    common = [wrapper, "-O2", "-Wall", "-Wextra", "-Werror", "-I" + str(prefix / "include")]
    link = ["-L" + str(prefix / "lib"), "-Wl,-rpath,/usr/pkg/lib", "-Wl,-rpath-link," + str(prefix / "lib")]
    for precision in ("double", "float"):
        lib = "fftw3f" if precision == "float" else "fftw3"
        options = ["-DUSE_FLOAT"] if precision == "float" else []
        run("test-" + precision + "-build", common + options + [PROBES / "fftw/tests/contract.c"]
            + link + ["-l" + lib + "_threads", "-l" + lib, "-lm", "-lpthread", "-o", tests / ("fftw-" + precision)])
    run("test-liquid-build", common + [PROBES / "liquid-dsp/tests/contract.c"]
        + link + ["-lliquid", "-lm", "-o", tests / "liquid-contract"])
    run("test-backend-build", common + ["-std=c11", "-I" + str(liquid / "include"),
        "-I" + str(patched), backend] + link + ["-lfftw3f", "-lm", "-o", tests / "backend-selection"])
    shutil.copyfile(PROBES / "dsp/test-armv7.sh", tests / "test.sh")
    share = prefix / "share/ember-dsp"
    (share / "licenses").mkdir(parents=True)
    for source, name in ((fftw / "COPYING", "licenses/FFTW-GPL-2.0-or-later"),
                         (liquid / "LICENSE", "licenses/liquid-dsp-MIT"),
                         (PROBES / "dsp/LICENSE", "licenses/EmberBSD-MIT"),
                         (Path(__file__), "cross-armv7.py"),
                         (PROBES / "dsp/test-armv7.sh", "test-armv7.sh"),
                         (patch, patch.name)):
        shutil.copyfile(source, share / name)
    for component in ("fftw", "liquid-dsp"):
        for name in ("sources.tsv", "PROVENANCE.md"):
            shutil.copyfile(PROBES / component / name, share / (component + "-" + name))
    for artifact in list((prefix / "lib").glob("*.so.*")) + list(tests.iterdir()):
        if artifact.is_symlink() or artifact.name.endswith(".sh"):
            continue
        elf = output([compiler / "bin" / (TARGET + "-readelf"), "-h", "-A", artifact])
        if not re.search(r"Machine:\s+ARM\b", elf) or "Tag_ABI_VFP_args: VFP registers" not in elf:
            raise RuntimeError("Invalid ARM hard-float artifact: " + str(artifact))
    imports = output([compiler / "bin" / (TARGET + "-nm"), "-u", prefix / "lib/libliquid.so"])
    for name in ("fftwf_plan_dft_1d", "fftwf_execute", "fftwf_destroy_plan"):
        if not re.search(r"\b" + name + r"\b", imports):
            raise RuntimeError("Missing FFTW import: " + name)
    (work / "logs/fftw-imports.txt").write_text(imports + "\n")
    receipt = {"target": TARGET, "gcc_version": VERSION, "sources": sources,
        "patch_sha256": digest(patch), "recipe_sha256": digest(__file__),
        "compiler_sha256": digest(cc), "sysroot_libc_sha256": digest(sysroot / "usr/lib/libc.so"),
        "sysroot_param_sha256": digest(sysroot / "usr/include/sys/param.h"),
        "runtime_tested": False}
    (work / "inputs.json").write_text(json.dumps(receipt, indent=2) + "\n")
    files = sorted(path for path in (work / "stage").rglob("*") if path.is_file() and not path.is_symlink())
    (work / "files.sha256").write_text("".join(f"{digest(path)}  {path.relative_to(work / 'stage')}\n" for path in files))
    (work / "complete").write_text("EmberBSD earmv7hf GCC16 DSP stage; target execution remains required.\n")
    print("Staged under " + str(work / "stage"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compiler", type=path_arg, help="GCC16 prefix")
    parser.add_argument("sysroot", type=path_arg, help="Coherent EmberBSD earmv7hf sysroot")
    parser.add_argument("work", type=path_arg, help="Unused build directory")
    parser.add_argument("--source-cache", type=path_arg, help="Directory with pinned source archives")
    parser.add_argument("--jobs", type=positive, default=4)
    parser.add_argument("--make", default="make", help="Host GNU make executable")
    args = parser.parse_args()
    os.umask(0o022)
    try:
        build(args)
    except (OSError, ValueError, RuntimeError, argparse.ArgumentTypeError,
            subprocess.CalledProcessError, tarfile.TarError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
