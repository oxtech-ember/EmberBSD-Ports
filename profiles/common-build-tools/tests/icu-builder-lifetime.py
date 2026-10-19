#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the actual ICU iterator implementation.
"""Compare the pinned ICU builder constructor with its lifetime repair."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tarfile
import time
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sdk-source", "archive", "native-prefix", "native-cxx",
                 "cross-tools", "sysroot", "patch", "cppcheck", "clang", "work"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--memory", required=True, choices=("asan-no-leaks",))
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15):
        parser.error("Python 3.15 is required")
    sdk = Path(args.sdk_source).resolve(strict=True)
    sys.path.insert(0, str(sdk / "src"))
    import emberbsd_sdk
    from emberbsd_sdk import paths, process
    from emberbsd_sdk.errors import CommandError
    if emberbsd_sdk.API_VERSION != 1:
        parser.error("SDK library API 1 is required")
    root = Path(__file__).resolve().parents[1]
    recipe = root / "recipes/textproc/icu"
    archive = Path(paths.canonical_existing(args.archive))
    native = Path(paths.canonical_existing(args.native_prefix))
    tools = Path(paths.canonical_existing(args.cross_tools))
    sysroot = Path(paths.canonical_existing(args.sysroot))
    work = Path(paths.canonical_new(args.work))
    for item in (sdk, root, archive, native, tools, sysroot):
        paths.reject_overlap(str(work), str(item))
    if archive.name != "icu4c-78.3-sources.tgz":
        parser.error("use the pinned ICU 78.3 source archive")
    info = (recipe / "distinfo").read_text()
    blob = archive.read_bytes()
    for name, constructor in (("BLAKE2s", hashlib.blake2s), ("SHA512", hashlib.sha512)):
        expected = re.search(rf"^{name} \({re.escape(archive.name)}\) = ([0-9a-f]+)$", info, re.M)
        if expected is None or constructor(blob).hexdigest() != expected[1]:
            raise ValueError("ICU archive checksum mismatch: " + name)
    work.mkdir()
    receipt = dict(archive_sha256=hashlib.sha256(blob).hexdigest(), commands=[],
                   memory_scope="ASan/UBSan instrument the actual builder translation unit; "
                                "linked native ICU archives are not instrumented",
                   memory_gap="Memcheck and LeakSanitizer are unavailable on the qualified "
                              "Darwin AArch64 host; detect_leaks=0 is explicit",
                   target_scope="GCC16 AArch64 compile; Clang is analysis only")
    environment = dict(os.environ)
    environment.update(ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
                       UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")

    def run(label, argv, *, cwd=None):
        command = [str(item) for item in argv]
        started = time.monotonic()
        try:
            result = process.capture(command, cwd=str(cwd) if cwd else None, env=environment)
            status, output, errors = result.returncode, result.stdout, result.stderr
        except CommandError as error:
            status, output, errors = error.returncode, error.stdout, error.stderr
        (work / (label + ".stdout")).write_bytes(output)
        (work / (label + ".stderr")).write_bytes(errors)
        receipt["commands"].append(dict(label=label, argv=command, cwd=str(cwd),
                                         status=status, seconds=time.monotonic()-started))
        (work / "results.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return status, output, errors

    def good(label, argv, *, cwd=None):
        status, output, errors = run(label, argv, cwd=cwd)
        if status:
            raise ValueError(f"{label} failed ({status}); inspect {work}")
        return output, errors

    for label, program in (("native-cxx-version", args.native_cxx),
                           ("gcc-version", tools / "aarch64--netbsd-g++"),
                           ("cppcheck-version", args.cppcheck), ("clang-version", args.clang)):
        good(label, [program, "--version"])
    version, _ = good("gcc-release", [tools / "aarch64--netbsd-g++", "-dumpfullversion"])
    if version.strip() != b"16.2.0":
        raise ValueError("the common GCC16.2 compiler is required")
    machine, _ = good("gcc-target", [tools / "aarch64--netbsd-g++", "-dumpmachine"])
    if machine.strip() != b"aarch64--netbsd":
        raise ValueError("the AArch64 NetBSD GCC16 compiler is required")
    good("native-icu-version", [native / "bin/icu-config", "--version"])
    if (work / "native-icu-version.stdout").read_text().strip() != "78.3":
        raise ValueError("the full native ICU 78.3 provider is required")
    baseline = work / "baseline"
    baseline.mkdir()
    with tarfile.open(archive) as source:
        source.extractall(baseline, filter="data")
    base = baseline / "icu/source"
    affected = ("i18n/collationiterator.h", "i18n/collationdatabuilder.cpp")
    upstream_hashes = {name: hashlib.sha256((base / name).read_bytes()).hexdigest()
                       for name in affected}
    repair = "patch-i18n_collation-builder-lifetime"
    patches = []
    for patch in sorted((recipe / "patches").glob("patch-*")):
        expected = re.search(rf"^SHA1 \({re.escape(patch.name)}\) = ([0-9a-f]+)$", info, re.M)
        body = b"".join(line for line in patch.read_bytes().splitlines(keepends=True)
                        if b"$NetBSD" not in line)
        if expected is None or hashlib.sha1(body).hexdigest() != expected[1]:
            raise ValueError("ICU patch checksum mismatch: " + patch.name)
        if patch.name != repair:
            good("apply-" + patch.name, [args.patch, "-f", "-F", "0", "-p0", "-i", patch], cwd=base)
            patches.append(patch.name)
    if upstream_hashes != {name: hashlib.sha256((base / name).read_bytes()).hexdigest()
                           for name in affected}:
        raise ValueError("an imported patch changed the upstream lifetime baseline")
    receipt.update(upstream_source_sha256=upstream_hashes, imported_patches=patches)
    patched = work / "patched"
    shutil.copytree(baseline, patched, symlinks=True)
    port = patched / "icu/source"
    good("apply-lifetime", [args.patch, "-f", "-F", "0", "-p0", "-i", recipe / "patches" / repair], cwd=port)
    fixture = Path(__file__).with_suffix(".cpp")
    receipt["fixture_sha256"] = hashlib.sha256(fixture.read_bytes()).hexdigest()
    implementation = ["-DU_ALL_IMPLEMENTATION", "-DU_I18N_IMPLEMENTATION", "-DU_ATTRIBUTE_DEPRECATED="]
    native_flags = ["-std=c++17", "-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    layouts = set()
    for label, source in (("baseline", base), ("patched", port)):
        executable = work / (label + "-native")
        includes = ["-I" + str(source / part) for part in ("i18n", "common")]
        good(label + "-native-build", [args.native_cxx, *native_flags, *implementation,
             *includes, fixture, *[native / "lib" / ("libicu" + lib + ".a")
                                 for lib in ("i18n", "uc", "data")], "-o", executable])
        for fill in (0, 1, 90, 165, 255):
            modes = ("constructor", "functional") if label == "patched" or fill == 0 else ("constructor",)
            for mode in modes:
                status, output, errors = run(f"{label}-{mode}-{fill}", [executable, mode, str(fill)])
                if label == "baseline" and fill:
                    if status != 1 or b"builder cached an unconstructed trie" not in errors:
                        raise ValueError("the poisoned real baseline did not detect the lifetime defect")
                elif status or b"PASS:" not in output:
                    raise ValueError(f"the real {label} {mode} fixture failed")
                if b"AddressSanitizer" in errors or b"runtime error:" in errors:
                    raise ValueError("ASan/UBSan failure in the ICU fixture")
                match = re.search(rb"layout=([0-9,]+)", output)
                if match:
                    layouts.add(match[1])
    if len(layouts) != 1:
        raise ValueError("the repair changed the observed ICU object layout")
    receipt["layout"] = next(iter(layouts)).decode()
    cxx = tools / "aarch64--netbsd-g++"
    target_flags = ["--sysroot=" + str(sysroot), "-std=c++17", "-O2", "-fPIC",
                    "-fstack-protector-strong", "-D_FORTIFY_SOURCE=2", "-D_REENTRANT",
                    "-DU_HAVE_ELF_H=1", "-W", "-Wall", "-pedantic", "-Wpointer-arith",
                    "-Wwrite-strings", "-Wno-long-long", *implementation]
    findings = {"cppcheck": {}, "clang": {}}
    for label, source in (("baseline", base), ("patched", port)):
        includes = ["-I" + str(source / part) for part in ("i18n", "common")]
        translation = source / affected[1]
        status, output, errors = run(label + "-gcc", [cxx, *target_flags, *includes,
                                     "-Werror=uninitialized", "-c", translation,
                                     "-o", work / (label + "-aarch64.o")])
        if label == "baseline":
            if status == 0 or b"uninitialized" not in errors or b"trie" not in errors:
                raise ValueError("GCC16 did not detect the real baseline constructor defect")
        elif status:
            raise ValueError("the patched target translation unit did not compile")
        preprocessed = work / (label + ".ii")
        good(label + "-preprocess", [cxx, *target_flags, *includes, "-E", translation, "-o", preprocessed])
        # Exact target preprocessing retains the selected macros, headers and LP64 data model.
        run(label + "-cppcheck", [args.cppcheck, "--language=c++", "--std=c++17",
            "--platform=unix64", "--enable=warning,style,performance,portability,information",
            "--inconclusive", "--xml", "--xml-version=2", "--error-exitcode=1", preprocessed])
        # Cppcheck models the standard library when its GCC16 header parser fails.
        # This pass retains the real ICU headers and the selected target macros.
        _, _, errors = run(label + "-cppcheck-icu-headers", [args.cppcheck,
            "--language=c++", "--std=c++17", "--platform=unix64", "--library=std,posix",
            "--check-level=exhaustive",
            "--enable=warning,style,performance,portability,information,missingInclude",
            "--inconclusive", "--xml", "--xml-version=2", "--error-exitcode=1",
            "-D__NetBSD__=1", "-D__aarch64__=1", "-D__LP64__=1", "-D__GNUC__=16",
            "-D__GNUC_MINOR__=2", "-D_REENTRANT=1", "-DU_HAVE_ELF_H=1",
            *implementation, *includes, translation])
        parsed = ET.fromstring(errors).findall("./errors/error")
        critical = {"syntaxError", "internalAstError", "internalError", "preprocessorErrorDirective"}
        if any(item.get("id") in critical for item in parsed):
            raise ValueError("Cppcheck did not complete the bounded ICU-header pass")
        findings["cppcheck"][label] = [
            (item.get("id"), item.get("msg"),
             tuple(str(Path(loc.get("file")).relative_to(source))
                   if Path(loc.get("file")).is_relative_to(source) else loc.get("file")
                   for loc in item.findall("location"))) for item in parsed]
        cxx_headers = sysroot / "usr/pkg/gcc16/include/c++"
        analysis_flags = ["--target=aarch64--netbsd11.0", "--sysroot=" + str(sysroot),
                          "-std=c++17", "-nostdinc++"]
        for include in (cxx_headers, cxx_headers / "aarch64--netbsd", cxx_headers / "backward"):
            analysis_flags.extend(("-isystem", str(include)))
        _, errors = good(label + "-clang-sa", [args.clang, *analysis_flags, *includes,
            "-D_REENTRANT", "-DU_HAVE_ELF_H=1", *implementation, "--analyze",
            "-Xanalyzer", "-analyzer-checker=core,cplusplus,unix,deadcode",
            "-Xanalyzer", "-analyzer-output=text", translation, "-o", work / (label + ".plist")])
        findings["clang"][label] = [
            (str(Path(match[0]).relative_to(source)), match[3], match[4])
            for match in re.findall(r"^(.+?):(\d+):(\d+): warning: (.+?) \[(.+?)\]$",
                                    errors.decode(), re.M)]
    if not any(item[2] == "core.uninitialized.Assign" for item in findings["clang"]["baseline"]):
        raise ValueError("Clang did not detect the baseline lifetime defect")
    if any(item[2] == "core.uninitialized.Assign" for item in findings["clang"]["patched"]):
        raise ValueError("Clang still detects an uninitialized assignment after repair")
    receipt["analyzers"] = {}
    for analyzer, results in findings.items():
        added = list((Counter(results["patched"]) - Counter(results["baseline"])).elements())
        removed = list((Counter(results["baseline"]) - Counter(results["patched"])).elements())
        receipt["analyzers"][analyzer] = dict(baseline=results["baseline"], patched=results["patched"],
                                             added=added, removed=removed)
        if added:
            raise ValueError("new unresolved " + analyzer + " findings; inspect " + str(work))
    receipt["analysis_gap"] = ("Cppcheck's complete GCC16-preprocessed input is not qualified; "
                               "the ICU-header pass uses standard-library models. Existing "
                               "source findings remain recorded without suppressions.")
    output, _ = good("target-object", [tools / "aarch64--netbsd-readelf", "-h", "-p", ".comment",
                                      work / "patched-aarch64.o"])
    if b"AArch64" not in output or b"GCC: (GNU) 16.2.0" not in output:
        raise ValueError("the target object has the wrong architecture or compiler")
    receipt["completed"] = True
    (work / "results.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"PASS: 16 actual-source lifetime cases, stable layout and causal GCC16 build; "
          f"inspect unchanged analyzer findings and the explicit analysis/memory gaps in {work}")


if __name__ == "__main__":
    main()
