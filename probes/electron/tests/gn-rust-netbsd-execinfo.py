#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted E12 regression).
"""Check the pinned NetBSD Rust std link dependency with GCC16."""

import sys

sys.dont_write_bytecode = True
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("use the selected host CPython 3.15")

import argparse
import hashlib
from pathlib import Path
import platform
import re

parser = argparse.ArgumentParser(description=__doc__)
for option in ("sdk-source", "ports-root", "source", "patch", "workspace",
               "sysroot", "target-cxx", "cppcheck", "clang"):
    parser.add_argument("--" + option, required=True, type=Path)
parser.add_argument("new_work", type=Path, metavar="NEW_WORK")
args = parser.parse_args()

if not args.sdk_source.is_absolute():
    parser.error("--sdk-source must be absolute")
SDK_SOURCE = args.sdk_source.resolve(strict=True)
SDK_SRC = SDK_SOURCE / "src"
SDK_PACKAGE = SDK_SRC / "emberbsd_sdk"
if not SDK_PACKAGE.is_dir():
    parser.error("--sdk-source must contain src/emberbsd_sdk")
sys.path.insert(0, str(SDK_SRC))

import emberbsd_sdk
from emberbsd_sdk import elf, errors, inventory, jsonio, paths, process
from emberbsd_sdk.errors import CommandError, SDKError

if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error("selected SDK source must provide API version 1")

# Check every SDK module imported by this runner, including relative imports.
SDK_MODULE_ORIGINS = {}
for module_name, module in tuple(sys.modules.items()):
    if module_name == "emberbsd_sdk" or module_name.startswith("emberbsd_sdk."):
        origin = getattr(module, "__file__", None)
        if not origin:
            parser.error(f"SDK module did not load from --sdk-source: {module_name}")
        origin = Path(origin).resolve(strict=True)
        if not origin.is_relative_to(SDK_PACKAGE.resolve(strict=True)):
            parser.error(f"SDK module did not load from --sdk-source: {module_name}")
        SDK_MODULE_ORIGINS[module_name] = str(origin)


def canonical_input(label, value):
    if not value.is_absolute():
        parser.error(f"--{label} must be absolute")
    try:
        return Path(paths.canonical_existing(str(value)))
    except SDKError as exc:
        parser.error(f"invalid --{label}: {exc}")


PORTS = canonical_input("ports-root", args.ports_root)
SOURCE = canonical_input("source", args.source)
PATCH = canonical_input("patch", args.patch)
WORKSPACE = canonical_input("workspace", args.workspace)
SYSROOT = canonical_input("sysroot", args.sysroot)
CXX = canonical_input("target-cxx", args.target_cxx)
CPPCHECK = canonical_input("cppcheck", args.cppcheck)
CLANG = canonical_input("clang", args.clang)
for label, directory in (("Ports", PORTS), ("source", SOURCE),
                         ("workspace", WORKSPACE)):
    if not directory.is_dir():
        parser.error(f"--{label} must name a directory")
LOCK_ROOT = Path(paths.canonical_existing(str(WORKSPACE / "obj")))
if SYSROOT != WORKSPACE / "sysroot":
    parser.error("--sysroot must be the canonical --workspace/sysroot")
if LOCK_ROOT != WORKSPACE / "obj":
    parser.error("SDK lock root must be the canonical --workspace/obj")

if not args.new_work.is_absolute():
    parser.error("NEW_WORK must be absolute")
if paths.entry(str(args.new_work)) is not None:
    parser.error("NEW_WORK must be a new path")
if not args.new_work.parent.is_dir():
    parser.error("NEW_WORK parent must exist")
try:
    ROOT = Path(paths.canonical_new(str(args.new_work)))
    if str(ROOT) != str(args.new_work):
        parser.error("NEW_WORK must use its canonical path")
    for label, boundary in (("SDK source", SDK_SOURCE), ("SDK workspace", WORKSPACE),
                            ("Ports", PORTS), ("Chromium source", SOURCE),
                            ("patch", PATCH)):
        paths.reject_overlap(str(ROOT), str(boundary))
except SDKError as exc:
    parser.error(f"unsafe NEW_WORK: {exc}")

BUILD_FILE = SOURCE / "build/rust/std/BUILD.gn"
RUST_STD_SOURCE = (SOURCE / "third_party/rust-toolchain/lib/rustlib/src/rust/"
                   "library/std/src/sys/pal/unix/mod.rs")
LIBEXECINFO = SYSROOT / "usr/lib/libexecinfo.so.0.0"
EXECINFO_HEADER = SYSROOT / "usr/include/execinfo.h"
if not BUILD_FILE.is_file() or not RUST_STD_SOURCE.is_file():
    parser.error("pinned Chromium source lacks the expected Rust standard-library inputs")

PATCH_TEXT = PATCH.read_text(encoding="utf-8")
patch_headers = [line for line in PATCH_TEXT.splitlines()
                 if line.startswith(("--- ", "+++ "))]
if patch_headers != ["--- a/build/rust/std/BUILD.gn",
                     "+++ b/build/rust/std/BUILD.gn"]:
    parser.error("patch must modify only build/rust/std/BUILD.gn")
added = [line[1:] for line in PATCH_TEXT.splitlines()
         if line.startswith("+") and not line.startswith("+++")]
removed = [line[1:] for line in PATCH_TEXT.splitlines()
           if line.startswith("-") and not line.startswith("---")]
if added != ['        "execinfo",'] or removed:
    parser.error("patch must add only the NetBSD execinfo library line")
if len([line for line in PATCH_TEXT.splitlines() if line.startswith("@@ ")]) != 1:
    parser.error("patch must contain one hunk")

SELECTOR = 'else if (target_os == "netbsd" && current_os == "netbsd") {'


def netbsd_public_libs(data):
    text = data.decode("utf-8", "strict")
    if text.count(SELECTOR) != 1:
        raise RuntimeError("expected one target/current NetBSD selector")
    begin = text.index("libs = [", text.index(SELECTOR)) + len("libs = [")
    end = text.index("]", begin)
    return re.findall(r'"([^"\n]+)"', text[begin:end])


def sha256_file(path):
    return inventory.sha256_file(str(path))


def hash_inputs(include_sysroot):
    inputs = {
        "chromium_build_gn": BUILD_FILE,
        "pinned_rust_std_source": RUST_STD_SOURCE,
        "patch": PATCH,
        "target_cxx": CXX,
    }
    if include_sysroot:
        inputs.update(execinfo_library=LIBEXECINFO,
                      execinfo_header=EXECINFO_HEADER)
    return {name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in inputs.items()}


ENV = process.sanitized_environment()
if not ENV.get("PATH"):
    parser.error("sanitized environment has no PATH")
PATCH_BIN = Path("/usr/bin/patch")
if not PATCH_BIN.is_file():
    parser.error("base-system /usr/bin/patch is required")

ROOT.mkdir()
LOGS = ROOT / "logs"
LOGS.mkdir()
commands = []


def invoke(name, argv, cwd, *, expected=(0,), input_bytes=None):
    argv = [str(value) for value in argv]
    failure = None
    try:
        result = process.capture(argv, cwd=str(cwd), env=ENV, input=input_bytes)
        returncode, stdout, stderr = 0, result.stdout, result.stderr
    except CommandError as command_error:
        failure = command_error
        returncode, stdout, stderr = (command_error.returncode,
                                      command_error.stdout, command_error.stderr)
        if returncode not in expected:
            (LOGS / f"{name}.stdout").write_bytes(stdout)
            (LOGS / f"{name}.stderr").write_bytes(stderr)
            commands.append({"name": name, "argv": argv, "cwd": str(cwd),
                             "returncode": returncode})
            raise
    if returncode not in expected:
        raise RuntimeError(f"{name}: unexpected exit status {returncode}")
    (LOGS / f"{name}.stdout").write_bytes(stdout)
    (LOGS / f"{name}.stderr").write_bytes(stderr)
    record = {"name": name, "argv": argv, "cwd": str(cwd),
              "returncode": returncode,
              "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
              "stderr_sha256": hashlib.sha256(stderr).hexdigest()}
    if input_bytes is not None:
        record["stdin_sha256"] = hashlib.sha256(input_bytes).hexdigest()
    commands.append(record)
    return result if returncode == 0 else failure


def patch_tree(name, original, *, reverse=False, dry_run=False):
    tree = ROOT / name
    target = tree / "build/rust/std/BUILD.gn"
    target.parent.mkdir(parents=True)
    target.write_bytes(original)
    argv = [PATCH_BIN]
    if reverse:
        argv.append("-R")
    argv += ["--batch", "--forward"]
    if dry_run:
        argv.append("--dry-run")
    argv += ["-p1", "-F0", "-i", PATCH]
    return invoke(name, argv, tree, expected=(0, 1))


try:
    source_bytes = BUILD_FILE.read_bytes()
    rust_source_text = RUST_STD_SOURCE.read_text(encoding="utf-8")
    netbsd_std = re.search(r'target_os = "netbsd" => \{([^}]*)\}',
                           rust_source_text, re.DOTALL)
    if not netbsd_std or netbsd_std.group(1).count('#[link(name = "execinfo")]') != 1:
        raise RuntimeError("pinned Rust std source lacks the NetBSD execinfo link")

    forward = patch_tree("patch-forward-check", source_bytes, dry_run=True)
    reverse = patch_tree("patch-reverse-check", source_bytes,
                         reverse=True, dry_run=True)
    if (forward.returncode == 0) == (reverse.returncode == 0):
        raise RuntimeError("source must match exactly one patch state")
    if forward.returncode == 0:
        baseline_bytes = source_bytes
        applied = patch_tree("patch-apply", baseline_bytes)
        if applied.returncode != 0:
            raise RuntimeError("strict patch application failed")
        patched_bytes = (ROOT / "patch-apply/build/rust/std/BUILD.gn").read_bytes()
    else:
        patched_bytes = source_bytes
        reversed_patch = patch_tree("patch-reverse", patched_bytes, reverse=True)
        if reversed_patch.returncode != 0:
            raise RuntimeError("strict reverse patch application failed")
        baseline_bytes = (ROOT / "patch-reverse/build/rust/std/BUILD.gn").read_bytes()

    needle = (b'      libs = [\n        "rt",\n        "pthread",\n      ]')
    replacement = (b'      libs = [\n        "execinfo",\n        "rt",\n        "pthread",\n      ]')
    if baseline_bytes.count(needle) != 1 or baseline_bytes.replace(needle, replacement, 1) != patched_bytes:
        raise RuntimeError("patch changed content beyond the single NetBSD execinfo line")
    baseline_libs = netbsd_public_libs(baseline_bytes)
    patched_libs = netbsd_public_libs(patched_bytes)
    if baseline_libs != ["rt", "pthread"] or patched_libs != ["execinfo", "rt", "pthread"]:
        raise RuntimeError("production NetBSD Rust link lists differ from expected")

    fixture = ROOT / "execinfo-link.cc"
    fixture.write_text("""#include <execinfo.h>
#include <stdlib.h>

int main() {
  void *frames[1] = {0};
  char **symbols = backtrace_symbols(frames, 1);
  free(symbols);
  return 0;
}
""", encoding="utf-8")

    # Do not inspect sysroot inputs outside this canonical shared read lease.
    external_before = hash_inputs(include_sysroot=False)
    with process.ContextLocks([str(SYSROOT)], str(LOCK_ROOT), shared=True):
        lease_before = hash_inputs(include_sysroot=True)
        if any(lease_before[name] != external_before[name]
               for name in external_before):
            raise RuntimeError("source, patch, or compiler changed before the shared lease")
        lib_header = elf.read_elf_header(LIBEXECINFO, machine=62, required_type=3)
        if lib_header is None:
            raise RuntimeError("libexecinfo is not an ELF64 little-endian x86_64 shared library")
        gcc_target = invoke("target-cxx-target", [CXX, "-dumpmachine"], ROOT)
        gcc_version = invoke("target-cxx-version", [CXX, "-dumpfullversion"], ROOT)
        if gcc_target.stdout.decode().strip() != "x86_64--netbsd":
            raise RuntimeError("selected GCC driver is not the x86_64 NetBSD target")
        if gcc_version.stdout.decode().strip() != "16.2.0":
            raise RuntimeError("selected GCC driver is not GCC 16.2.0")

        def link(name, libraries):
            output = ROOT / f"{name}.elf"
            gcc_lib = SYSROOT / "usr/pkg/gcc16/lib"
            gcc_libdir = gcc_lib / "gcc/x86_64--netbsd/16.2.0"
            argv = [CXX, "--sysroot=" + str(SYSROOT),
                    "-B" + str(gcc_libdir) + "/", "-B" + str(gcc_lib) + "/",
                    "-std=c++20", "-nostdinc++", "-nodefaultlibs",
                    "-Wall", "-Wextra", "-Werror", "-Wl,--no-undefined", fixture,
                    "-L" + str(gcc_lib), "-Wl,-rpath,/usr/pkg/gcc16/lib"]
            for directory in (SYSROOT / "lib", SYSROOT / "usr/lib", gcc_lib):
                argv.append("-Wl,-rpath-link," + str(directory))
            argv += ["-lc", "-lgcc_s", "-lm", "-lrt"]
            argv += ["-l" + library for library in libraries]
            argv += ["-o", output]
            return invoke(name, argv, ROOT, expected=(0, 1)), output

        baseline_link, _ = link("link-without-execinfo", baseline_libs)
        baseline_stderr = baseline_link.stderr.decode("utf-8", "replace")
        if (baseline_link.returncode != 1 or "undefined reference" not in baseline_stderr
                or "backtrace_symbols" not in baseline_stderr):
            raise RuntimeError("baseline did not fail on undefined backtrace_symbols")
        patched_link, patched_output = link("link-with-execinfo", patched_libs)
        if patched_link.returncode != 0:
            raise RuntimeError("patched NetBSD library list failed to link")
        linked_elf = elf.read_elf_header(patched_output, machine=62)
        if linked_elf is None or linked_elf["type"] not in (2, 3):
            raise RuntimeError("linked output is not an ELF64 little-endian x86_64 executable")

        predefines = invoke(
            "target-predefined-macros",
            [CXX, "--sysroot=" + str(SYSROOT),
             "-B" + str(SYSROOT / "usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0") + "/",
             "-B" + str(SYSROOT / "usr/pkg/gcc16/lib") + "/",
             "-dM", "-E", "-x", "c++", "-"], ROOT,
            input_bytes=b"#include <execinfo.h>\n")
        macro_map = {}
        for line in predefines.stdout.decode("utf-8", "replace").splitlines():
            match = re.fullmatch(r"#define ([A-Za-z_][A-Za-z0-9_]*) (.+)", line)
            if match:
                macro_map[match.group(1)] = match.group(2)
        macro_names = ["__GNUC__", "__GNUC_MINOR__", "__GNUC_PATCHLEVEL__",
                       "__NetBSD__", "__x86_64__", "_LP64", "__PTRDIFF_TYPE__",
                       "__SIZE_TYPE__", "__INTPTR_TYPE__", "__UINTPTR_TYPE__",
                       "__WCHAR_TYPE__", "__WINT_TYPE__", "__CHAR_BIT__",
                       "__SIZEOF_POINTER__", "__SIZEOF_LONG__", "__BYTE_ORDER__",
                       "__ORDER_LITTLE_ENDIAN__", "__INTMAX_TYPE__", "__UINTMAX_TYPE__"]
        if "__NetBSD_Version__" in macro_map:
            macro_names.append("__NetBSD_Version__")
        if any(name not in macro_map for name in macro_names):
            raise RuntimeError("GCC16 target predefined macro set is incomplete")
        cppcheck_args = ["-D" + name + "=" + macro_map[name] for name in macro_names]

        cppcheck_version = invoke("cppcheck-version", [CPPCHECK, "--version"], ROOT)
        clang_version = invoke("clang-version", [CLANG, "--version"], ROOT)
        cppcheck = invoke(
            "cppcheck", [CPPCHECK, "--language=c++", "--std=c++20",
                         "--platform=unix64",
                         "--enable=warning,style,performance,portability",
                         "--error-exitcode=1", *cppcheck_args,
                         "-I", SYSROOT / "usr/include", fixture], ROOT)
        clang = invoke(
            "clang-static-analyzer",
            [CLANG, "-target", "x86_64-unknown-netbsd",
             "--sysroot=" + str(SYSROOT), "-std=c++20", "-Wall", "-Wextra",
             "-Werror", "--analyze", "-Xanalyzer", "-analyzer-output=text",
             fixture], ROOT)
        if cppcheck.returncode or clang.returncode:
            raise RuntimeError("static analysis failed")

        lease_after = hash_inputs(include_sysroot=True)
        if lease_after != lease_before:
            raise RuntimeError("a source, toolchain, or sysroot input changed under the shared lease")

    external_after = hash_inputs(include_sysroot=False)
    if external_after != external_before:
        raise RuntimeError("a source, patch, or compiler changed across the shared lease")

    receipt = {
        "format": "emberbsd-e12-rust-execinfo-link-regression",
        "version": 2,
        "status": "PASS",
        "source": str(SOURCE),
        "baseline_build_gn_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "patched_build_gn_sha256": hashlib.sha256(patched_bytes).hexdigest(),
        "rust_std_source_sha256": lease_before["pinned_rust_std_source"]["sha256"],
        "patch": str(PATCH),
        "patch_sha256": lease_before["patch"]["sha256"],
        "runner": str(Path(__file__).resolve(strict=True)),
        "runner_sha256": sha256_file(Path(__file__).resolve(strict=True)),
        "baseline_public_dependent_libs": baseline_libs,
        "patched_public_dependent_libs": patched_libs,
        "fixture_sha256": sha256_file(fixture),
        "sdk_api_version": emberbsd_sdk.API_VERSION,
        "sdk_source": str(SDK_SOURCE),
        "sdk_module_origins": SDK_MODULE_ORIGINS,
        "workspace": str(WORKSPACE),
        "sysroot": str(SYSROOT),
        "shared_sysroot_lease": True,
        "non_sysroot_inputs_before_lease": external_before,
        "locked_inputs_before_checks": lease_before,
        "locked_inputs_after_checks": lease_after,
        "non_sysroot_inputs_after_lease": external_after,
        "target_cxx": str(CXX),
        "target_cxx_version": gcc_version.stdout.decode().strip(),
        "target_cxx_machine": gcc_target.stdout.decode().strip(),
        "libexecinfo_elf": lib_header,
        "linked_output_elf": linked_elf,
        "linked_output_sha256": sha256_file(patched_output),
        "cppcheck_version": cppcheck_version.stdout.decode().strip(),
        "clang_version": clang_version.stdout.decode().splitlines()[0],
        "host": platform.platform(),
        "limits": ["no Rust standard-library build", "no final Electron link",
                   "no target execution", "bounded C++ link and static-analysis fixture"],
        "commands": commands,
    }
    jsonio.write_json(str(ROOT / "receipt.json"), receipt, exclusive=True)
    print("PASS: NetBSD Rust execinfo C++ link dependency")
    print("receipt:", ROOT / "receipt.json")
except (SDKError, OSError, RuntimeError, UnicodeError, ValueError) as exc:
    print(f"FAIL: {exc}", file=sys.stderr)
    raise SystemExit(1)
