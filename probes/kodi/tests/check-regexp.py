#!/usr/bin/env python3
"""Build and check the actual Kodi 21.3 PCRE2 consumer with current providers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile

PATCHES = ("patch-pcre2-upstream", "patch-pcre2-match-lifetime",
           "patch-pcre2-named-captures", "patch-pcre2-owned-captures",
           "patch-pcre2-cmake-provider", "patch-pcre2-allocation-failures",
           "patch-pcre2-named-failure-state", "patch-pcre2-utf-error-offset")
FILES = ("CMakeLists.txt", "xbmc/utils/RegExp.cpp", "xbmc/utils/RegExp.h",
         "xbmc/utils/StringUtils.cpp", "xbmc/utils/StringUtils.h",
         "xbmc/utils/Utf8Utils.cpp", "xbmc/utils/Utf8Utils.h",
         "xbmc/utils/TimeFormat.h", "xbmc/utils/params_check_macros.h")
def verified(path, expected):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != expected:
        raise ValueError(f"source SHA256 differs: {path}")


def run(command, log, *, expected=0, env=None):
    result = subprocess.run(command, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, env=env,
                            timeout=180)
    log.write_text(result.stdout)
    if (result.returncode == 0) != (expected == 0):
        raise RuntimeError(f"unexpected status {result.returncode}; see {log}")
    return result.returncode


def cppcheck_findings(log, baseline_source, candidate_source):
    findings = []
    for line in log.read_text().splitlines():
        if re.search(r":\d+:\d+: (?:error|warning|style|performance|portability|information):", line):
            normalized = line.replace(str(baseline_source), str(candidate_source))
            normalized = re.sub(r":\d+:\d+: ", ": ", normalized)
            findings.append(normalized)
    return sorted(set(findings))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("kodi_archive", "fmt_archive", "native_pcre", "gcc", "sysroot", "work"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--native-cxx", default="c++")
    parser.add_argument("--analyzer", default="clang++")
    args = parser.parse_args()
    profile = Path(__file__).resolve().parents[1]
    manifest = json.loads((profile / "source.json").read_text())
    sources = {item["archive"]: item["sha256"] for item in manifest["sources"]}
    verified(args.kodi_archive, sources["xbmc-21.3-Omega.tar.gz"])
    verified(args.fmt_archive, sources["fmt-12.2.0.tar.gz"])
    patch_hashes = {Path(item["file"]).name: item["sha256"] for item in manifest["patches"]}
    for name, digest in patch_hashes.items():
        verified(profile / "patches" / name, digest)
    gcc = args.gcc.resolve()
    sysroot = args.sysroot.resolve()
    ember_root = sysroot.parent.parent
    build_root = ember_root / "build/obj"
    tmp_root = ember_root / "tmp"
    if args.work.exists() or args.work.is_symlink():
        parser.error("work must be a new directory")
    work = args.work.resolve()
    tmpdir = Path(os.environ.get("TMPDIR", "")).resolve()
    if not work.is_relative_to(build_root) or work == build_root:
        parser.error(f"work must be a new directory under {build_root}")
    if not tmpdir.is_relative_to(tmp_root) or not tmpdir.is_dir():
        parser.error(f"set TMPDIR to an existing directory under {tmp_root}")
    if not work.parent.is_dir():
        parser.error("work parent must already exist")
    if work == sysroot or work.is_relative_to(sysroot) or sysroot.is_relative_to(work):
        parser.error("work and sysroot must not overlap")
    if work == gcc or work.is_relative_to(gcc) or gcc.is_relative_to(work):
        parser.error("work and compiler prefix must not overlap")
    disk = subprocess.check_output(["df", "-Pk", str(work.parent)], text=True)
    cxx = gcc / "bin/aarch64--netbsd-g++"
    version = subprocess.check_output([cxx, "-dumpfullversion"], text=True).strip()
    target = subprocess.check_output([cxx, "-dumpmachine"], text=True).strip()
    if version != "16.2.0" or target != "aarch64--netbsd":
        parser.error("select the common GCC 16.2.0 AArch64 toolchain")
    work.mkdir(parents=True)
    source = work / "source"
    source.mkdir()
    (work / "preflight.txt").write_text(
        f"work={work}\nTMPDIR={tmpdir}\nsysroot={sysroot}\nGCC16={gcc}\n"
        f"native_pcre2={args.native_pcre.resolve()}\n{disk}")
    with tarfile.open(args.kodi_archive) as archive:
        for relative in FILES:
            destination = source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.extractfile("xbmc-21.3-Omega/" + relative).read())
    fmt = work / "fmt"
    fmt.mkdir()
    with tarfile.open(args.fmt_archive) as archive:
        for member in archive:
            if member.isfile() and member.name.startswith("fmt-12.2.0/include/"):
                relative = Path(member.name).relative_to("fmt-12.2.0/include")
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("invalid fmt source member")
                destination = fmt / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.extractfile(member).read())
    for name in PATCHES[:3]:
        run(["patch", "-f", "-F0", "-p1", "-d", str(source), "-i",
             str(profile / "patches" / name)], work / (name + ".log"))
    for name in ("RegExp.cpp", "RegExp.h", "Utf8Utils.h"):
        shutil.copyfile(source / "xbmc/utils" / name, work / name)
    shutil.copyfile(work / "RegExp.cpp", work / "baseline-RegExp.cpp")
    text = (source / "xbmc/utils/StringUtils.cpp").read_text()
    selected = []
    for name in ("asciidigitvalue", "asciixdigitvalue"):
        start = text.index("int StringUtils::" + name + "(")
        end = text.index("\n}\n", start) + 3
        selected.append(text[start:end])
    (work / "StringFunctions.cpp").write_text(
        '#include "utils/StringUtils.h"\n' + "\n".join(selected))
    includes = [f"-I{profile}/tests", f"-I{source}/xbmc", f"-I{work}", f"-isystem{fmt}"]
    units = [str(work / "RegExp.cpp"), str(work / "StringFunctions.cpp"),
             str(source / "xbmc/utils/Utf8Utils.cpp"), str(profile / "tests/regexp.cpp")]
    native = [args.native_cxx, "-std=c++17", "-DFMT_HEADER_ONLY", "-g", "-O1",
              "-fsanitize=address,undefined", "-fno-omit-frame-pointer", *includes,
              f"-I{args.native_pcre}/include", *units,
              f"-L{args.native_pcre}/lib", "-lpcre2-8"]
    run([*native, "-o", str(work / "baseline")], work / "baseline-build.log")
    leak_detection = int(sys.platform != "darwin")
    loader_variable = "DYLD_LIBRARY_PATH" if sys.platform == "darwin" else "LD_LIBRARY_PATH"
    env = dict(os.environ, ASAN_OPTIONS=f"symbolize=0:detect_leaks={leak_detection}:abort_on_error=1",
               UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    native_library_dir = str(args.native_pcre.resolve() / "lib")
    prior_library_path = env.get(loader_variable)
    env[loader_variable] = native_library_dir + (os.pathsep + prior_library_path if prior_library_path else "")
    for suffix, arguments, marker in (
            ("copy", ["--copy"], "heap-use-after-free"),
            ("named", ["--named-after-failure"], "AddressSanitizer:")):
        run([str(work / "baseline"), *arguments], work / f"baseline-{suffix}.log",
            expected=1, env=env)
        if marker not in (work / f"baseline-{suffix}.log").read_text():
            raise RuntimeError(f"baseline did not reproduce {suffix}")
    run(["patch", "-f", "-F0", "-p1", "-d", str(source), "-i",
         str(profile / "patches" / PATCHES[3])], work / (PATCHES[3] + ".log"))
    (source / "cmake/modules").mkdir(parents=True, exist_ok=True)
    run(["patch", "-f", "-F0", "-p1", "-d", str(source), "-i",
         str(profile / "patches" / PATCHES[4])], work / (PATCHES[4] + ".log"))
    run(["patch", "-f", "-F0", "-p1", "-d", str(source), "-i",
         str(profile / "patches" / PATCHES[5])], work / (PATCHES[5] + ".log"))
    run(["patch", "-f", "-F0", "-p1", "-d", str(source), "-i",
         str(profile / "patches" / PATCHES[6])], work / (PATCHES[6] + ".log"))
    run(["patch", "-f", "-F0", "-p1", "-d", str(source), "-i",
         str(profile / "patches" / PATCHES[7])], work / (PATCHES[7] + ".log"))
    shutil.copyfile(source / "xbmc/utils/RegExp.cpp", work / "RegExp.cpp")
    run([*native, "-o", str(work / "native")], work / "native-build.log")
    run([str(work / "native")], work / "native-run.log", env=env)
    runtime = sysroot / "usr/pkg/gcc16"
    flags = [f"--sysroot={sysroot}", f"-B{runtime}/lib/gcc/{target}/16.2.0/",
             f"-B{runtime}/lib/", "-nostdinc++", f"-isystem{runtime}/include/c++",
             f"-isystem{runtime}/include/c++/{target}", "-std=c++17", "-DFMT_HEADER_ONLY",
             "-g", "-O2", *includes, f"-isystem{sysroot}/usr/pkg/include"]
    target_units = [*units, str(profile / "tests/pcre2-faults.cpp")]
    cross_command = [str(cxx), *flags, "-DKODI_PCRE2_FAULT_TESTS", *target_units,
                     "-Wl,--wrap=pcre2_compile_context_create_8",
                     "-Wl,--wrap=pcre2_match_context_create_8",
                     "-Wl,--wrap=pcre2_match_data_create_8",
                     f"-L{runtime}/lib", f"-L{sysroot}/usr/pkg/lib",
                     "-lpcre2-8", "-Wl,-rpath,/usr/pkg/gcc16/lib:/usr/pkg/lib",
                     f"-Wl,-rpath-link,{runtime}/lib", f"-Wl,-rpath-link,{sysroot}/usr/pkg/lib",
                     "-o", str(work / "regexp-aarch64")]
    run(cross_command, work / "cross-build.log")
    database = [{"directory": str(work), "file": unit,
                 "arguments": [str(cxx), *flags, "-DKODI_PCRE2_FAULT_TESTS", "-c", unit]}
                for unit in target_units]
    (work / "compile_commands.json").write_text(json.dumps(database, indent=2) + "\n")
    baseline_database = json.loads(json.dumps(database))
    baseline_source = work / "baseline-RegExp.cpp"
    candidate_source = work / "RegExp.cpp"
    for entry in baseline_database:
        if entry["file"] == str(candidate_source):
            entry["file"] = str(baseline_source)
        entry["arguments"] = [str(baseline_source) if arg == str(candidate_source) else arg
                              for arg in entry["arguments"]]
    baseline_database_path = work / "compile_commands-baseline.json"
    baseline_database_path.write_text(json.dumps(baseline_database, indent=2) + "\n")
    cppcheck = shutil.which("cppcheck")
    if cppcheck is None:
        parser.error("Cppcheck is required for the C++ source checks")
    cppcheck_commands = []
    for label, database_path in (("baseline", baseline_database_path),
                                 ("patched", work / "compile_commands.json")):
        cppcheck_build = work / f"cppcheck-{label}"
        cppcheck_build.mkdir()
        command = [cppcheck, "--enable=warning,performance,portability",
                   f"--project={database_path}", f"--cppcheck-build-dir={cppcheck_build}"]
        run(command, work / f"cppcheck-{label}.log")
        cppcheck_commands.append(shlex.join(command))
    baseline_findings = cppcheck_findings(work / "cppcheck-baseline.log",
                                          baseline_source, candidate_source)
    patched_findings = cppcheck_findings(work / "cppcheck-patched.log",
                                         baseline_source, candidate_source)
    new_findings = sorted(set(patched_findings) - set(baseline_findings))
    (work / "cppcheck-diff.json").write_text(json.dumps(
        {"baseline": baseline_findings, "patched": patched_findings,
         "new": new_findings,
         "baseline_scope": "Kodi 21.3 after upstream PCRE2 migration and named-capture API adaptation"},
        indent=2) + "\n")
    if new_findings:
        raise RuntimeError("Cppcheck found new diagnostics after EmberBSD patches; see cppcheck-diff.json")
    analyzer = shutil.which(args.analyzer)
    if analyzer is None:
        parser.error("Clang Static Analyzer is required for the C++ source checks")
    analyzer_version = subprocess.check_output([analyzer, "--version"], text=True).splitlines()[0]
    analyzer_dir = work / "clang-sa"
    analyzer_dir.mkdir()
    analyzer_records = []
    for index, entry in enumerate(database):
        analyzer_command = list(entry["arguments"])
        analyzer_command[0] = analyzer
        analyzer_command.remove("-c")
        analyzer_command[1:1] = ["--target=aarch64-unknown-netbsd", "--analyze",
                                 "-Xanalyzer", "-analyzer-output=text"]
        analyzer_command.extend(["-o", str(analyzer_dir / f"unit-{index}.plist")])
        log = analyzer_dir / f"unit-{index}.log"
        run(analyzer_command, log)
        analyzer_records.append({"file": entry["file"], "command": shlex.join(analyzer_command),
                                 "log": log.name})
    native_output = (work / "native-run.log").read_text().strip()
    native_version = next(line.removeprefix("PCRE2 runtime: ")
                          for line in native_output.splitlines()
                          if line.startswith("PCRE2 runtime: "))
    results = {"kodi_sha256": sources["xbmc-21.3-Omega.tar.gz"],
               "fmt_sha256": sources["fmt-12.2.0.tar.gz"],
               "gcc": version, "target": target,
               "native_cxx": subprocess.check_output([args.native_cxx, "--version"], text=True),
               "native_result": native_output,
               "native_pcre2_prefix": str(args.native_pcre.resolve()),
               "native_pcre2_loader": loader_variable,
               "native_pcre2_version": native_version,
               "cppcheck": subprocess.check_output([cppcheck, "--version"], text=True).strip(),
               "cppcheck_commands": cppcheck_commands,
               "cppcheck_baseline_findings": baseline_findings,
               "cppcheck_patched_findings": patched_findings,
               "cppcheck_new_findings": new_findings,
               "clang_static_analyzer": analyzer_version,
               "clang_static_analyzer_target": "aarch64-unknown-netbsd",
               "clang_static_analyzer_units": analyzer_records,
               "memory_check": "ASan/UBSan; not Valgrind",
               "leak_detection": bool(leak_detection),
               "cross_sha256": hashlib.sha256((work / "regexp-aarch64").read_bytes()).hexdigest(),
               "target_execution": "pending",
               "target_fault_injection": "compiled; target execution pending",
               "cross_command": shlex.join(cross_command)}
    (work / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(results["native_result"])
    print("PASS: causal ASan use-after-free and null-code controls; GCC16 AArch64 ELF; target execution is separate")


if __name__ == "__main__":
    main()
