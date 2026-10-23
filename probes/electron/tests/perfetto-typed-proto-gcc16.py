#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted E12 regression).
"""Check the pinned Perfetto typed-field diagnostic with target GCC16."""

import sys

sys.dont_write_bytecode = True
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("use the selected host CPython 3.15")

import argparse
import hashlib
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
for option in ("sdk-source", "ports-root", "source-root", "gn-out",
               "patch", "cxx", "workspace"):
    parser.add_argument("--" + option, required=True, type=Path)
parser.add_argument("work_dir", type=Path, metavar="NEW_WORK")
args = parser.parse_args()

if not args.work_dir.is_absolute():
    parser.error("NEW_WORK must be absolute")
if not args.sdk_source.is_absolute():
    parser.error("--sdk-source must be absolute")
SDK_SOURCE = args.sdk_source.resolve(strict=True)
SDK_PACKAGE = SDK_SOURCE / "src/emberbsd_sdk"
if not (SDK_PACKAGE / "__init__.py").is_file():
    parser.error("--sdk-source must contain src/emberbsd_sdk")
sys.path.insert(0, str(SDK_SOURCE / "src"))

import emberbsd_sdk
from emberbsd_sdk import elf, errors, inventory, jsonio, paths, process
from emberbsd_sdk.errors import CommandError, SDKError

if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error("selected SDK source must provide integer API version 1")
SDK_MODULES = {}
for module_name, module in tuple(sys.modules.items()):
    if module_name == "emberbsd_sdk" or module_name.startswith("emberbsd_sdk."):
        origin = getattr(module, "__file__", None)
        if not origin:
            parser.error("SDK module has no source origin: " + module_name)
        resolved = Path(origin).resolve(strict=True)
        if not resolved.is_relative_to(SDK_PACKAGE.resolve(strict=True)):
            parser.error("SDK module did not load from --sdk-source: " + module_name)
        SDK_MODULES[module_name] = str(resolved)


def existing(label, value):
    if not value.is_absolute():
        parser.error("--" + label + " must be absolute")
    try:
        return Path(paths.canonical_existing(str(value)))
    except SDKError as exc:
        parser.error("invalid --" + label + ": " + str(exc))


PORTS = existing("ports-root", args.ports_root)
SOURCE = existing("source-root", args.source_root)
GN_OUT = existing("gn-out", args.gn_out)
PATCH = existing("patch", args.patch)
CXX = existing("cxx", args.cxx)
WORKSPACE = existing("workspace", args.workspace)
if not PORTS.is_dir() or not SOURCE.is_dir() or not GN_OUT.is_dir() or not WORKSPACE.is_dir():
    parser.error("Ports, source, GN output, and workspace paths must be directories")
SYSROOT = Path(paths.canonical_existing(str(WORKSPACE / "sysroot")))
LOCK_ROOT = Path(paths.canonical_existing(str(WORKSPACE / "obj")))
if SYSROOT != WORKSPACE / "sysroot":
    parser.error("SDK sysroot must be the canonical workspace/sysroot")
if LOCK_ROOT != WORKSPACE / "obj":
    parser.error("SDK lock root must be the canonical workspace/obj")
if not CXX.is_file():
    parser.error("--cxx must name the target compiler")
if not args.work_dir.parent.is_dir():
    parser.error("NEW_WORK parent must exist")
if paths.entry(str(args.work_dir)) is not None:
    parser.error("NEW_WORK must be a new path")
try:
    WORK = Path(paths.canonical_new(str(args.work_dir)))
except SDKError as exc:
    parser.error("invalid NEW_WORK: " + str(exc))
if WORK != args.work_dir:
    parser.error("NEW_WORK must use its canonical path")
for label, root in (("Ports", PORTS), ("Chromium source", SOURCE),
                    ("SDK source", SDK_SOURCE), ("SDK workspace", WORKSPACE),
                    ("sysroot", SYSROOT), ("GN output", GN_OUT)):
    if WORK.is_relative_to(root) or root.is_relative_to(WORK):
        parser.error("NEW_WORK must be separate from " + label)

PINNED_HEADER = "src/trace_processor/importers/proto/typed_proto_field.h"
BASELINE_SHA256 = "064003e605ea4324ab383c268e0021a1a6709e5241245092bea1d24ffb1b8b9d"
PATCH_SHA256 = "bbe6625d9d1147f3d3427bba31847004a15f63c051e09a60355e2f09319982c9"
PATCHED_SHA256 = "da7ce1bf9045f915f58a1f04d7d827de8990e0891a68bd21153d8614b291f221"
if inventory.sha256_file(PATCH) != PATCH_SHA256:
    parser.error("patch hash does not match this regression pin")
PERFETTO = SOURCE / "third_party/perfetto"
HEADER = PERFETTO / PINNED_HEADER
FIXTURE_DIR = Path(__file__).resolve().parent
SUPPORTED = FIXTURE_DIR / "perfetto-typed-proto-supported.cpp"
UNSUPPORTED = FIXTURE_DIR / "perfetto-typed-proto-unsupported.cpp"
PERFETTO_FLAGS = GN_OUT / "gen/third_party/perfetto/build_config/perfetto_build_flags.h"
for path in (HEADER, SUPPORTED, UNSUPPORTED, PERFETTO_FLAGS,
             SOURCE / "third_party/libc++/src/include/__config",
             SOURCE / "buildtools/third_party/libc++/__config_site"):
    if not path.is_file():
        parser.error("missing source or generated input: " + str(path))
PATCH_TOOL = shutil.which("patch")
GIT = shutil.which("git")
if not PATCH_TOOL or not GIT:
    parser.error("git and POSIX patch are required")
PATCH_TOOL = Path(PATCH_TOOL).resolve(strict=True)
GIT = Path(GIT).resolve(strict=True)

source_paths = [HEADER, SUPPORTED, UNSUPPORTED, PERFETTO_FLAGS,
                SOURCE / "third_party/libc++/src/include/__config",
                SOURCE / "buildtools/third_party/libc++/__config_site", PATCH]
source_hashes_before = {str(path): inventory.sha256_file(path) for path in source_paths}
if source_hashes_before[str(HEADER)] not in (BASELINE_SHA256, PATCHED_SHA256):
    parser.error("production header must match the exact pinned baseline or carried patch")
source_revision = process.capture([str(GIT), "-C", str(SOURCE), "rev-parse", "HEAD"],
                                  env=process.sanitized_environment()).stdout.decode().strip()

WORK.mkdir(parents=True, exist_ok=False)
LOGS = WORK / "logs"
LOGS.mkdir()
HEADER_RELATIVE = Path("src/trace_processor/importers/proto/typed_proto_field.h")


def invoke(name, argv, *, cwd, expected=None):
    argv = [str(item) for item in argv]
    try:
        result = process.capture(argv, cwd=str(cwd), env=process.sanitized_environment())
        status, stdout, stderr = result.returncode, result.stdout, result.stderr
    except CommandError as exc:
        status, stdout, stderr = exc.returncode, exc.stdout, exc.stderr
    (LOGS / (name + ".stdout")).write_bytes(stdout)
    (LOGS / (name + ".stderr")).write_bytes(stderr)
    row = {"name": name, "argv": argv, "cwd": str(cwd), "returncode": status,
           "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
           "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
           "stdout_bytes": len(stdout), "stderr_bytes": len(stderr)}
    jsonio.write_json(LOGS / (name + ".json"), row)
    if expected is not None and status != expected:
        raise RuntimeError(name + " returned " + str(status) + "; inspect " + str(LOGS))
    return row, stdout, stderr


def apply_patch(overlay, *, name):
    return invoke(name, [PATCH_TOOL, "-p1", "-F", "0", "-i", PATCH],
                  cwd=overlay, expected=0)


def normalize_overlay_pair(name, before, after, input_hash):
    """Normalize either accepted source state into baseline and patched overlays."""
    if input_hash == PATCHED_SHA256:
        invoke(name + "-reverse-patch",
               [PATCH_TOOL, "-R", "-p1", "-F", "0", "-i", PATCH],
               cwd=before, expected=0)
    elif input_hash != BASELINE_SHA256:
        raise RuntimeError(name + " has an unknown input header hash")

    before_header = before / HEADER_RELATIVE
    after_header = after / HEADER_RELATIVE
    if inventory.sha256_file(before_header) != BASELINE_SHA256:
        raise RuntimeError(name + " did not normalize its before overlay to baseline")
    # The after overlay starts from the same input state. Reset it to the
    # normalized baseline before applying the forward patch.
    after_header.write_bytes(before_header.read_bytes())
    apply_patch(after, name=name + "-forward-patch")
    if inventory.sha256_file(after_header) != PATCHED_SHA256:
        raise RuntimeError(name + " did not normalize its after overlay to patched")
    return {
        "input_state": "baseline" if input_hash == BASELINE_SHA256 else "already-patched",
        "input_sha256": input_hash,
        "before_sha256": inventory.sha256_file(before_header),
        "after_sha256": inventory.sha256_file(after_header),
    }


def make_overlay_pair(name, header_bytes):
    before = WORK / (name + "-before")
    after = WORK / (name + "-after")
    for overlay in (before, after):
        path = overlay / HEADER_RELATIVE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(header_bytes)
    input_hash = hashlib.sha256(header_bytes).hexdigest()
    result = normalize_overlay_pair(name, before, after, input_hash)
    return before, after, result


MACHINES = {"x86_64--netbsd": 62, "aarch64--netbsd": 183}


def compile_command(overlay, fixture, output, dependency, *, unknown_type=False):
    gcc_lib = SYSROOT / "usr/pkg/gcc16/lib"
    gcc_libdir = gcc_lib / "gcc" / target / version
    argv = [str(CXX), "--sysroot=" + str(SYSROOT),
            "-B" + str(gcc_libdir) + "/", "-B" + str(gcc_lib) + "/",
            "-std=gnu++23", "-nostdinc++", "-O2", "-Wall", "-Werror",
            "-fno-strict-overflow", "-fno-strict-aliasing", "-fno-exceptions",
            "-fno-rtti", "-pthread", "-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_EXTENSIVE",
            "-D_LIBCPP_DISABLE_VISIBILITY_ANNOTATIONS",
            "-D_LIBCXXABI_DISABLE_VISIBILITY_ANNOTATIONS",
            "-D_LIBCPP_INSTRUMENTED_WITH_ASAN=0", "-DPERFETTO_IMPLEMENTATION",
            "-DOFFICIAL_BUILD", "-DNDEBUG", "-DNVALGRIND",
            "-DDYNAMIC_ANNOTATIONS_ENABLED=0",
            "-I", str(overlay), "-I", str(SOURCE), "-I", str(GN_OUT / "gen"),
            "-I", str(SOURCE / "buildtools/third_party/libc++"),
            "-I", str(PERFETTO), "-I", str(PERFETTO / "src"),
            "-I", str(PERFETTO / "src/profiling/memory/include"),
            "-I", str(PERFETTO / "include"),
            "-I", str(GN_OUT / "gen/third_party/perfetto/build_config"),
            "-I", str(GN_OUT / "gen/third_party/perfetto"),
            "-I", str(SOURCE / "third_party/protobuf/src"),
            "-isystem", str(SOURCE / "third_party/libc++/src/include"),
            "-isystem", str(SOURCE / "third_party/libc++abi/src/include"),
            "-MMD", "-MF", str(dependency), "-MT", str(output),
            "-c", str(fixture), "-o", str(output)]
    if unknown_type:
        argv.insert(argv.index("-c"), "-DPERFETTO_TEST_SCHEMA_TYPE=Type::kUnknown")
    return argv


def run_compile(name, overlay, fixture, *, expect, expected_text=None,
                forbidden_text=None, unknown_type=False):
    output = WORK / (name + ".o")
    dependency = WORK / (name + ".d")
    argv = compile_command(overlay, fixture, output, dependency,
                           unknown_type=unknown_type)
    row, stdout, stderr = invoke(name, argv, cwd=WORK, expected=expect)
    diagnostic = (stdout + stderr).decode("utf-8", "replace")
    if expected_text and expected_text not in diagnostic:
        raise RuntimeError(name + " missed expected diagnostic " + repr(expected_text))
    if forbidden_text and forbidden_text in diagnostic:
        raise RuntimeError(name + " emitted forbidden diagnostic " + repr(forbidden_text))
    if expect == 0:
        header = elf.read_elf_header(output, machine=COMPILER_MACHINE, required_type=1)
        if header is None:
            raise RuntimeError(name + " did not produce a target ELF object")
        row["object"] = {**header, "sha256": inventory.sha256_file(output),
                         "size_bytes": output.stat().st_size}
        jsonio.write_json(LOGS / (name + ".json"), row, exclusive=False)
    return row, diagnostic


with process.ContextLocks([str(SYSROOT)], str(LOCK_ROOT), shared=True):
    machine_row, machine_out, _ = invoke("compiler-target", [CXX, "-dumpmachine"],
                                         cwd=WORK, expected=0)
    target = machine_out.decode("utf-8", "strict").strip()
    version_row, version_out, _ = invoke("compiler-version", [CXX, "-dumpfullversion"],
                                         cwd=WORK, expected=0)
    version = version_out.decode("utf-8", "strict").strip()
    if target not in MACHINES or version.split(".", 1)[0] != "16":
        raise RuntimeError("target compiler must be GCC16 for NetBSD amd64 or arm64")
    COMPILER_MACHINE = MACHINES[target]
    macros, macro_output, _ = invoke(
        "compiler-netbsd-macros",
        [CXX, "--sysroot=" + str(SYSROOT), "-B" + str(SYSROOT / "usr/pkg/gcc16/lib/gcc" / target / version) + "/",
         "-B" + str(SYSROOT / "usr/pkg/gcc16/lib") + "/", "-dM", "-E", "-x", "c++", "-"],
        cwd=WORK, expected=0)
    if b"#define __NetBSD__ 1" not in macro_output:
        raise RuntimeError("target GCC does not define __NetBSD__")

    current_hash = source_hashes_before[str(HEADER)]
    current_header = HEADER.read_bytes()
    OVERLAY_BEFORE, OVERLAY_AFTER, current_state = make_overlay_pair(
        "source-current-state", current_header)

    # Exercise the other accepted input state with the same production patch.
    alternate_seed = WORK / "alternate-state-seed"
    alternate_header = alternate_seed / HEADER_RELATIVE
    alternate_header.parent.mkdir(parents=True, exist_ok=True)
    alternate_header.write_bytes(current_header)
    if current_hash == BASELINE_SHA256:
        apply_patch(alternate_seed, name="derive-already-patched-input")
        alternate_bytes = alternate_header.read_bytes()
        alternate_hash = hashlib.sha256(alternate_bytes).hexdigest()
        if alternate_hash != PATCHED_SHA256:
            raise RuntimeError("forward patch did not derive exact patched input")
    elif current_hash == PATCHED_SHA256:
        invoke("derive-baseline-input",
               [PATCH_TOOL, "-R", "-p1", "-F", "0", "-i", PATCH],
               cwd=alternate_seed, expected=0)
        alternate_bytes = alternate_header.read_bytes()
        alternate_hash = hashlib.sha256(alternate_bytes).hexdigest()
        if alternate_hash != BASELINE_SHA256:
            raise RuntimeError("reverse patch did not derive exact baseline input")
    else:
        raise RuntimeError("unexpected source header state")
    _, _, alternate_state = make_overlay_pair("alternate-input-state", alternate_bytes)
    normalization_cases = {
        current_state["input_state"]: current_state,
        alternate_state["input_state"]: alternate_state,
    }
    if set(normalization_cases) != {"baseline", "already-patched"}:
        raise RuntimeError("overlay normalization did not cover both accepted inputs")

    supported, _ = run_compile("supported-candidate", OVERLAY_AFTER, SUPPORTED,
                                expect=0)
    unsupported_before, before_diagnostic = run_compile(
        "unsupported-baseline", OVERLAY_BEFORE, UNSUPPORTED, expect=1,
        expected_text="Unsupported proto schema type",
        forbidden_text="unused-function", unknown_type=True)
    if "tautological-compare" not in before_diagnostic:
        raise RuntimeError("baseline did not reproduce GCC16 tautological-compare")
    before_errors = [line for line in before_diagnostic.splitlines()
                     if ": error:" in line]
    if (len(before_errors) != 2
            or not any("tautological-compare" in line for line in before_errors)
            or not any("static assertion failed" in line for line in before_errors)):
        raise RuntimeError("baseline produced diagnostics outside the two expected errors")
    unsupported_after, after_diagnostic = run_compile(
        "unsupported-candidate", OVERLAY_AFTER, UNSUPPORTED, expect=1,
        expected_text="Unsupported proto schema type",
        forbidden_text="tautological-compare", unknown_type=True)
    after_errors = [line for line in after_diagnostic.splitlines()
                    if ": error:" in line]
    if (len(after_errors) != 1
            or "static assertion failed" not in after_errors[0]
            or "tautological-compare" in after_errors[0]):
        raise RuntimeError("candidate produced diagnostics outside the intended static assertion")

source_hashes_after = {str(path): inventory.sha256_file(path) for path in source_paths}
if source_hashes_after != source_hashes_before:
    raise RuntimeError("a source, generated input, patch, or fixture changed during the test")
revision_after = process.capture([str(GIT), "-C", str(SOURCE), "rev-parse", "HEAD"],
                                 env=process.sanitized_environment()).stdout.decode().strip()
if revision_after != source_revision:
    raise RuntimeError("Chromium source revision changed during the test")

receipt = {
    "schema": 1,
    "status": "PASS",
    "chromium_revision": source_revision,
    "production_header": PINNED_HEADER,
    "source_header_state": "baseline" if current_hash == BASELINE_SHA256 else "already-patched",
    "source_input_sha256_before": source_hashes_before,
    "source_input_sha256_after": source_hashes_after,
    "patch_sha256": PATCH_SHA256,
    "patched_header_sha256": PATCHED_SHA256,
    "overlay_normalization_cases": normalization_cases,
    "target": {"triple": target, "gcc_version": version,
               "compiler_sha256": inventory.sha256_file(CXX),
               "elf_machine": COMPILER_MACHINE},
    "sdk_api": emberbsd_sdk.API_VERSION,
    "sdk_modules": SDK_MODULES,
    "cases": {
        "supported_candidate": supported,
        "unsupported_baseline": {"returncode": unsupported_before["returncode"],
                                  "requires_static_assert": True,
                                  "requires_tautological_compare": True},
        "unsupported_candidate": {"returncode": unsupported_after["returncode"],
                                  "requires_static_assert": True,
                                  "forbids_tautological_compare": True},
    },
    "objects_executed": False,
    "scope": "This bounded fixture exercises the production TypedProtoField header and verifies a supported enum result plus the unsupported-enum compile-time rejection. The actual trace_processor_context.cc production translation unit remains the causal GCC16 before/after check; this runner does not build Electron or execute target code.",
}
jsonio.write_json(LOGS / "receipt.json", receipt)
print("PASS: GCC16 NetBSD typed-proto diagnostic regression; see " + str(LOGS / "receipt.json"))
