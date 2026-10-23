#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted E12 libc++ source regression).
"""Compare pinned libc++ headers with the carried GCC 16 portability patch."""
import sys

sys.dont_write_bytecode = True
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("use the selected host CPython 3.15")

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct

parser = argparse.ArgumentParser(description=__doc__)
for name in ("sdk-source", "ports-root", "source-root", "patch", "cxx", "sysroot"):
    parser.add_argument("--" + name, required=True, type=Path)
parser.add_argument("--work-dir", required=True, type=Path)
parser.add_argument("--recursive-patch", type=Path,
                     help="optional follow-up GCC16 recursion fix, applied after --patch")
parser.add_argument("--workspace", type=Path,
                     help="canonical SDK workspace; required with --recursive-patch")
args = parser.parse_args()

if not args.work_dir.is_absolute():
    parser.error("--work-dir must be an absolute path")
SDK_SOURCE, PORTS, SOURCE, PATCH, CXX, SYSROOT = (
    path.resolve(strict=True) for path in
    (args.sdk_source, args.ports_root, args.source_root, args.patch,
     args.cxx, args.sysroot)
)
RECURSIVE_PATCH = (args.recursive_patch.resolve(strict=True)
                   if args.recursive_patch else None)
WORKSPACE = args.workspace.resolve(strict=True) if args.workspace else None
WORK = args.work_dir.resolve()
if RECURSIVE_PATCH is not None and WORKSPACE is None:
    parser.error("--workspace is required with --recursive-patch")
if WORKSPACE is not None:
    if not WORKSPACE.is_dir():
        parser.error("--workspace must name an existing SDK workspace")
    if SYSROOT != WORKSPACE / "sysroot":
        parser.error("--sysroot must be the canonical --workspace/sysroot")
    LOCK_ROOT = WORKSPACE / "obj"
    if not LOCK_ROOT.is_dir():
        parser.error("SDK lock root must be the canonical --workspace/obj")
else:
    LOCK_ROOT = None
SEPARATE_ROOTS = [("Ports root", PORTS), ("Chromium source", SOURCE),
                  ("SDK source", SDK_SOURCE), ("target sysroot", SYSROOT)]
if WORKSPACE is not None:
    SEPARATE_ROOTS.append(("SDK workspace", WORKSPACE))
for label, root in SEPARATE_ROOTS:
    if WORK.is_relative_to(root) or root.is_relative_to(WORK):
        parser.error("--work-dir must be separate from " + label)
if WORK.exists():
    parser.error("--work-dir must name a new, unused directory")

SDK_PACKAGE = SDK_SOURCE / "src/emberbsd_sdk"
if not (SDK_PACKAGE / "__init__.py").is_file():
    parser.error("selected SDK source has no emberbsd_sdk API")
sys.path.insert(0, str(SDK_SOURCE / "src"))
import emberbsd_sdk
if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error("selected SDK must provide integer API version 1")
if Path(emberbsd_sdk.__file__).resolve().parent != SDK_PACKAGE.resolve():
    parser.error("emberbsd_sdk must come from selected SDK source")
from emberbsd_sdk import errors, inventory, jsonio, process
SDK_MODULES = (emberbsd_sdk, errors, inventory, jsonio, process)
if any(not Path(module.__file__).resolve().is_relative_to(SDK_PACKAGE.resolve())
       for module in SDK_MODULES):
    parser.error("all imported SDK modules must come from selected SDK source")
capture = process.capture
CommandError = errors.CommandError
sha256_file = inventory.sha256_file
write_json = jsonio.write_json

LIBCXX = SOURCE / "third_party/libc++/src"
LIBCXX_INCLUDE = LIBCXX / "include"
LIBCXXABI_INCLUDE = SOURCE / "third_party/libc++abi/src/include"
CONFIG_INCLUDE = SOURCE / "buildtools/third_party/libc++"
PIN = "b16984ce99c702355a5b2b4c52574e82cec41fb9"
PINNED_HEADERS = {
    "include/string": "78dbb4c318727e34f19b79d5a89bd9815171a8bc0f557b47c6b1a10277976575",
    "include/__functional/function.h": "87ac62703ff11165111aca0c4c9ab0dc6a5b38718282ae8c2f2f09f473971869",
}
PATCH_SHA256 = "c37ab9f8425c66dc65a0cdaa8962ca596d83bf6888080bde399cb9a82803e99b"
PATCHED_HEADERS = {
    "include/string": "b3fb1fc528c748dce31239daee767eef56f4d78f3273381eb2cbb0273f7e7a35",
    "include/__functional/function.h": "b5110bdc2bac02b2540d9155d32bb877ee79b9316ea228e097e802d87eaf4514",
}

for path in (LIBCXX, LIBCXX_INCLUDE, LIBCXXABI_INCLUDE, CONFIG_INCLUDE,
             SOURCE / "buildtools/third_party/libc++/__config_site"):
    if not path.exists():
        parser.error("missing pinned libc++ input: " + str(path))
if sha256_file(PATCH) != PATCH_SHA256:
    parser.error("carried patch hash does not match this regression pin")
LIBCXX_HEAD = capture(["git", "-C", str(LIBCXX), "rev-parse", "HEAD"], cwd=LIBCXX).stdout.decode().strip()
try:
    capture(["git", "-C", str(LIBCXX), "merge-base", "--is-ancestor", PIN, LIBCXX_HEAD], cwd=LIBCXX)
except CommandError:
    parser.error("the pinned libc++ revision must be an ancestor of the current checkout")

FIXTURE_DIR = Path(__file__).resolve().parent
FIXTURES = {
    "string-max-size": FIXTURE_DIR / "libcxx-string-max-size.cpp",
    "function-sbo": FIXTURE_DIR / "libcxx-function-sbo.cpp",
    "memory-semantics": FIXTURE_DIR / "libcxx-memory-semantics.cpp",
}
if RECURSIVE_PATCH is not None:
    FIXTURES["recursive-function"] = FIXTURE_DIR / "libcxx-function-recursive.cpp"
for path in FIXTURES.values():
    if not path.is_file():
        parser.error("missing regression fixture: " + str(path))

PATCH_TOOL = shutil.which("patch")
GIT = shutil.which("git")
if PATCH_TOOL is None or GIT is None:
    parser.error("git and POSIX patch are required")
PATCH_TOOL = Path(PATCH_TOOL).resolve(strict=True)
GIT = Path(GIT).resolve(strict=True)

# Record only the explicit inputs read by this test. Header bytes come from the
# exact libc++ commit, even if the source worktree has a local edit.
source_paths = [
    LIBCXX / "include/string",
    LIBCXX / "include/__functional/function.h",
    SOURCE / "buildtools/third_party/libc++/__config_site",
    *FIXTURES.values(), PATCH,
]
if RECURSIVE_PATCH is not None:
    source_paths.append(RECURSIVE_PATCH)
source_hashes_before = {str(path): sha256_file(path) for path in source_paths}
source_header_hashes = {
    relative: sha256_file(LIBCXX / relative)
    for relative in PINNED_HEADERS
}
if source_header_hashes == PINNED_HEADERS:
    SOURCE_HEADER_STATE = "pinned-baseline"
elif source_header_hashes == PATCHED_HEADERS:
    SOURCE_HEADER_STATE = "exact-carried-patch"
else:
    parser.error("source headers must match either the pinned baseline or exact carried patch")
WORK.mkdir(parents=True, exist_ok=False)
LOGS = WORK / "logs"
LOGS.mkdir()
commands = []
ENV = {
    "PATH": str(CXX.parent) + os.pathsep + "/usr/bin:/bin",
    "LC_ALL": "C",
    "LANG": "C",
    "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(WORK),
}


def run(name, argv, *, cwd, expected=None):
    argv = list(map(str, argv))
    try:
        result = capture(argv, cwd=cwd, env=ENV)
        status, stdout, stderr = result.returncode, result.stdout, result.stderr
    except CommandError as error:
        status, stdout, stderr = error.returncode, error.stdout, error.stderr
    (LOGS / (name + ".stdout")).write_bytes(stdout)
    (LOGS / (name + ".stderr")).write_bytes(stderr)
    record = {"name": name, "argv": argv, "cwd": str(cwd), "returncode": status}
    commands.append(record)
    write_json(LOGS / "commands.json", commands, exclusive=False)
    if expected is not None and status != expected:
        raise AssertionError(name + " returned " + str(status) + "; see " + str(LOGS))
    return status, stdout, stderr


def git_blob(relative):
    result = capture([str(GIT), "-C", str(LIBCXX), "show", PIN + ":" + relative], cwd=LIBCXX, env=ENV)
    data = result.stdout
    actual = hashlib.sha256(data).hexdigest()
    if actual != PINNED_HEADERS[relative]:
        raise AssertionError("unexpected pinned blob for " + relative + ": " + actual)
    return data


def write_overlay(tree, headers):
    for relative, data in headers.items():
        output = tree / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)


def apply_patch(tree, patch_path=PATCH, *, name="patch-apply"):
    run(name, [PATCH_TOOL, "-p1", "-F", "0", "-i", patch_path], cwd=tree, expected=0)


EXPECTED_ELF_MACHINES = {
    "aarch64--netbsd": 183,
    "x86_64--netbsd": 62,
}


def compiler_identity():
    status, stdout, stderr = run("compiler-target", [CXX, "-dumpmachine"], cwd=WORK, expected=0)
    target = stdout.decode("utf-8", "strict").strip()
    status, stdout, stderr = run("compiler-version", [CXX, "-dumpfullversion"], cwd=WORK, expected=0)
    version = stdout.decode("utf-8", "strict").strip()
    if target not in EXPECTED_ELF_MACHINES:
        raise AssertionError("target compiler must be a supported exact NetBSD triple, got " + target)
    if version.split(".", 1)[0] != "16":
        raise AssertionError("target compiler must be GCC 16, got " + version)
    return {
        "target": target,
        "version": version,
        "sha256": sha256_file(CXX),
        "expected_elf_machine": EXPECTED_ELF_MACHINES[target],
    }


def inspect_elf_object(path):
    header = path.read_bytes()[:20]
    if len(header) != 20 or header[:4] != b"\x7fELF":
        raise AssertionError("successful compile did not produce an ELF object: " + str(path))
    if header[4] != 2:
        raise AssertionError("target object must be ELFCLASS64: " + str(path))
    if header[5] != 1:
        raise AssertionError("target object must be little-endian: " + str(path))
    object_type, machine = struct.unpack_from("<HH", header, 16)
    if object_type != 1:
        raise AssertionError("target object must have ELF type ET_REL: " + str(path))
    if machine != COMPILER["expected_elf_machine"]:
        raise AssertionError("ELF machine does not match compiler target: " + str(path))
    return {
        "elf_class": 64,
        "endianness": "little",
        "type": "ET_REL",
        "machine": machine,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


COMPILER = compiler_identity()
BASELINE = {
    relative: git_blob(relative)
    for relative in PINNED_HEADERS
}
BEFORE = WORK / "before"
AFTER = WORK / "after"
write_overlay(BEFORE, BASELINE)
write_overlay(AFTER, BASELINE)
apply_patch(AFTER)
for relative, expected in PATCHED_HEADERS.items():
    if sha256_file(AFTER / relative) != expected:
        raise AssertionError("patched header hash mismatch for " + relative)
AFTER_RECURSIVE = None
RECURSIVE_FUNCTION_HEADER = None
if RECURSIVE_PATCH is not None:
    if sha256_file(RECURSIVE_PATCH) != "e9fd9113e4c3c227c5691d65b60f3d5d7a490cb74b0575b0daacd4bf8ea26998":
        raise AssertionError("follow-up recursive patch hash does not match this regression pin")
    AFTER_RECURSIVE = WORK / "after-recursive"
    shutil.copytree(AFTER, AFTER_RECURSIVE)
    apply_patch(AFTER_RECURSIVE, RECURSIVE_PATCH, name="recursive-patch-apply")
    RECURSIVE_FUNCTION_HEADER = "082ccbfbd834d7e96a95fd7c07da8eafba32efe62b8192c183dfa5910bc71e05"
    if sha256_file(AFTER_RECURSIVE / "include/__functional/function.h") != RECURSIVE_FUNCTION_HEADER:
        raise AssertionError("follow-up recursive function header hash mismatch")

COMMON = [
    CXX,
    "--sysroot=" + str(SYSROOT),
    "-nostdinc++",
    "-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_EXTENSIVE",
    "-D_LIBCPP_DISABLE_VISIBILITY_ANNOTATIONS",
    "-D_LIBCPPABI_DISABLE_VISIBILITY_ANNOTATIONS",
    "-D_LIBCPP_INSTRUMENTED_WITH_ASAN=0",
    "-fno-rtti",
    "-Wall", "-Werror", "-O2", "-fno-strict-overflow", "-fno-strict-aliasing",
    "-pthread",
    "-I", "{overlay}/include",
    "-I", CONFIG_INCLUDE,
    "-isystem", LIBCXX_INCLUDE,
    "-isystem", LIBCXXABI_INCLUDE,
]


compile_artifacts = []


def compile_case(name, overlay, fixture, standard, *, exceptions=False, expected=0):
    output = WORK / (name + ".o")
    argv = [str(item).format(overlay=overlay) for item in COMMON]
    if exceptions:
        argv.append("-fexceptions")
    else:
        argv.append("-fno-exceptions")
    argv += ["-std=" + standard, "-c", fixture, "-o", output]
    status, stdout, stderr = run(name, argv, cwd=WORK, expected=expected)
    if status == 0:
        if not output.is_file():
            raise AssertionError(name + " succeeded without creating an object file")
        compile_artifacts.append({"name": name, "object": str(output), **inspect_elf_object(output)})
    return status, (stdout + stderr).decode("utf-8", "replace")


def compile_regressions():
    # The string baseline fails its compile-time contract checks. The function
    # fixture uses only public std::function operations and must compile against
    # both versions; causal GCC array-bounds evidence comes from the production
    # unix_task_runner and weak_runner translation units recorded separately.
    status, diagnostic = compile_case("baseline-string", BEFORE, FIXTURES["string-max-size"], "gnu++23", expected=1)
    if "max_size" not in diagnostic and "static assertion failed" not in diagnostic:
        raise AssertionError("baseline string failure did not match the max_size regression")
    status, diagnostic = compile_case("patched-string", AFTER, FIXTURES["string-max-size"], "gnu++23")
    compile_case("baseline-function-gnu++11", BEFORE, FIXTURES["function-sbo"], "gnu++11")
    compile_case("baseline-function-gnu++14", BEFORE, FIXTURES["function-sbo"], "gnu++14")
    for standard in ("gnu++11", "gnu++14"):
        compile_case("patched-function-" + standard, AFTER, FIXTURES["function-sbo"], standard)
    # Compile the executable behavior fixture with exceptions enabled, but do not
    # run a NetBSD target binary on the host.
    compile_case("patched-memory-semantics", AFTER, FIXTURES["memory-semantics"], "gnu++14", exceptions=True)
    if AFTER_RECURSIVE is not None:
        # This recursive std::function fixture is a compile/API control only.
        # It is not the causal reproducer; the actual Perfetto host_impl.cc TU
        # supplies the before/after GCC16 diagnostic evidence.
        compile_case("recursive-function-before-follow-up", AFTER, FIXTURES["recursive-function"], "gnu++14")
        compile_case("recursive-function-after-follow-up", AFTER_RECURSIVE, FIXTURES["recursive-function"], "gnu++14")

if WORKSPACE is None:
    compile_regressions()
else:
    # Target compiler invocations read the selected shared sysroot under an SDK
    # shared context lease. This is required for the optional follow-up patch.
    with process.ContextLocks([str(SYSROOT)], str(LOCK_ROOT), shared=True):
        compile_regressions()

source_hashes_after = {str(path): sha256_file(path) for path in source_paths}
if source_hashes_after != source_hashes_before:
    raise AssertionError("an input file changed during the regression")
receipt = {
    "schema": 1,
    "libcxx_revision": PIN,
    "libcxx_worktree_head": LIBCXX_HEAD,
    "libcxx_pin_is_ancestor": True,
    "libcxx_source_header_state": SOURCE_HEADER_STATE,
    "libcxx_source_header_sha256": source_header_hashes,
    "chromium_source_root": str(SOURCE),
    "libcxx_include": str(LIBCXX_INCLUDE),
    "libcxx_config": str(SOURCE / "buildtools/third_party/libc++/__config_site"),
    "target_sysroot": str(SYSROOT),
    "compiler": COMPILER,
    "patch_sha256": sha256_file(PATCH),
    "recursive_patch_sha256": sha256_file(RECURSIVE_PATCH) if RECURSIVE_PATCH else None,
    "recursive_patched_function_header_sha256": RECURSIVE_FUNCTION_HEADER,
    "baseline_header_sha256": PINNED_HEADERS,
    "patched_header_sha256": PATCHED_HEADERS,
    "source_input_sha256_before": source_hashes_before,
    "source_input_sha256_after": source_hashes_after,
    "tests": [
        {"name": row["name"], "returncode": row["returncode"]}
        for row in commands
    ],
    "successful_compile_objects": compile_artifacts,
    "runtime_executed": False,
    "runtime_limit": "Target execution is deferred until an ABI-matching NetBSD libc++ runtime is available; this compile-only runner does not link or execute target objects.",
}
write_json(LOGS / "receipt.json", receipt)
print("PASS: pinned-header regression compiled for " + COMPILER["target"] + "; every successful object is validated as 64-bit little-endian NetBSD ET_REL")
print("receipt: " + str(LOGS / "receipt.json"))
