#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted E12 regression).
"""Check Perfetto Murmur output and reproduce GCC16 production diagnostics."""

import sys

sys.dont_write_bytecode = True
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("use the selected host CPython 3.15")

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil

parser = argparse.ArgumentParser(description=__doc__)
for option in ("sdk-source", "ports-root", "source-root", "gn-out", "cxx",
               "sysroot", "workspace", "ninja", "host-cxx", "host-sdk", "patch"):
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
from emberbsd_sdk import inventory, jsonio, paths, process
from emberbsd_sdk.errors import CommandError, SDKError

if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error("selected SDK source must provide integer API version 1")
for module_name, module in tuple(sys.modules.items()):
    if module_name == "emberbsd_sdk" or module_name.startswith("emberbsd_sdk."):
        origin = getattr(module, "__file__", None)
        if not origin or not Path(origin).resolve(strict=True).is_relative_to(
                SDK_PACKAGE.resolve(strict=True)):
            parser.error("SDK module did not load from --sdk-source: " + module_name)


def existing(label, value):
    if not value.is_absolute():
        parser.error("--" + label + " must be absolute")
    try:
        return Path(paths.canonical_existing(str(value)))
    except SDKError as exc:
        parser.error("invalid --" + label + ": " + str(exc))


SDK = existing("sdk-source", args.sdk_source)
PORTS = existing("ports-root", args.ports_root)
SOURCE = existing("source-root", args.source_root)
OUT = existing("gn-out", args.gn_out)
CXX = existing("cxx", args.cxx)
SYSROOT = existing("sysroot", args.sysroot)
WORKSPACE = existing("workspace", args.workspace)
NINJA = existing("ninja", args.ninja)
HOST_CXX = existing("host-cxx", args.host_cxx)
HOST_SDK = existing("host-sdk", args.host_sdk)
PATCH = existing("patch", args.patch)
if not all(path.is_dir() for path in (PORTS, SOURCE, OUT, SYSROOT, WORKSPACE, HOST_SDK)):
    parser.error("Ports, source, GN output, sysroot, and workspace must be directories")
if not all(path.is_file() for path in (CXX, NINJA, HOST_CXX, PATCH)):
    parser.error("compiler, Ninja, and patch paths must be files")
if SYSROOT != WORKSPACE / "sysroot":
    parser.error("--sysroot must be the canonical SDK workspace/sysroot")
LOCK_ROOT = Path(paths.canonical_existing(str(WORKSPACE / "obj")))
if LOCK_ROOT != WORKSPACE / "obj":
    parser.error("--workspace must expose its canonical obj lock root")
if not args.work_dir.parent.is_dir():
    parser.error("NEW_WORK parent must exist")
if paths.entry(str(args.work_dir)) is not None:
    parser.error("NEW_WORK must be a new path")
try:
    WORK = Path(paths.canonical_new(str(args.work_dir)))
except SDKError as exc:
    parser.error("invalid NEW_WORK: " + str(exc))
for label, root in (("Ports", PORTS), ("Chromium source", SOURCE),
                    ("SDK source", SDK), ("SDK workspace", WORKSPACE),
                    ("sysroot", SYSROOT), ("GN output", OUT)):
    if WORK.is_relative_to(root) or root.is_relative_to(WORK):
        parser.error("NEW_WORK must be separate from " + label)

PINNED_SOURCE = "0f678fa0d9c6e21f26b16c3a6c43aebefc86caaa"
PINNED_PERFETTO = "2b7d39719d3d4b5ff45bcf5c451706e48d26f965"
PATCH_SHA256 = "1078f58a454d067408e78fbaa237bd2b62774379f6bff49e658a91cc069ff2e3"
if inventory.sha256_file(PATCH) != PATCH_SHA256:
    parser.error("patch hash does not match this regression pin")
if "target_os = \"netbsd\"" not in (OUT / "args.gn").read_text():
    parser.error("GN args must select the NetBSD target")
if "is_clang = false" not in (OUT / "args.gn").read_text():
    parser.error("GN args must select GCC")
if not (OUT / "build.ninja").is_file():
    parser.error("GN output must contain build.ninja")

GIT = shutil.which("git")
PATCH_TOOL = shutil.which("patch")
if not GIT or not PATCH_TOOL:
    parser.error("git and POSIX patch must be available on PATH")
GIT = Path(GIT).resolve(strict=True)
PATCH_TOOL = Path(PATCH_TOOL).resolve(strict=True)
PERFETTO = SOURCE / "third_party/perfetto"


def capture(argv, *, cwd=None):
    try:
        return process.capture([str(item) for item in argv],
                              cwd=str(cwd) if cwd else None,
                              env=process.sanitized_environment())
    except CommandError as exc:
        return exc


source_rev = capture([GIT, "-C", SOURCE, "rev-parse", "HEAD"]).stdout.decode().strip()
perfetto_rev = capture([GIT, "-C", PERFETTO, "rev-parse", "HEAD"]).stdout.decode().strip()
if source_rev != PINNED_SOURCE or perfetto_rev != PINNED_PERFETTO:
    parser.error("source or Perfetto revision does not match the regression pin")

WORK.mkdir(parents=True, exist_ok=False)
LOGS = WORK / "logs"
OBJECTS = WORK / "objects"
BEFORE = WORK / "before"
AFTER = WORK / "after"
for directory in (LOGS, OBJECTS, BEFORE, AFTER):
    directory.mkdir()


def invoke(name, argv, *, cwd=None, expected=None):
    result = capture(argv, cwd=cwd)
    status = result.returncode
    stdout, stderr = result.stdout, result.stderr
    (LOGS / (name + ".stdout")).write_bytes(stdout)
    (LOGS / (name + ".stderr")).write_bytes(stderr)
    if expected is not None and status != expected:
        raise RuntimeError(name + " returned " + str(status) + "; inspect " + str(LOGS))
    return {"name": name, "argv": [str(item) for item in argv],
            "cwd": str(cwd) if cwd else None, "returncode": status,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "stdout_bytes": len(stdout), "stderr_bytes": len(stderr)}, stderr


RELATIVE_FILES = (
    Path("include/perfetto/ext/base/murmur_hash.h"),
    Path("src/tracing/console_interceptor.cc"),
)


def git_blob(relative):
    result = capture([GIT, "-C", PERFETTO, "show",
                      PINNED_PERFETTO + ":" + relative.as_posix()])
    if result.returncode:
        raise RuntimeError("cannot read pinned source file " + relative.as_posix())
    return result.stdout


for overlay in (BEFORE, AFTER):
    for relative in RELATIVE_FILES:
        path = overlay / "third_party/perfetto" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(git_blob(relative))


def patch_overlay(overlay, reverse=False):
    argv = [PATCH_TOOL]
    if reverse:
        argv.append("-R")
    argv += ["-p1", "-F0", "-i", PATCH]
    return invoke("patch-" + ("reverse" if reverse else "forward") + "-" + overlay.name,
                  argv, cwd=overlay / "third_party/perfetto", expected=0)[0]


# The baseline and patched source hashes must both be known states in the live tree.
patch_overlay(AFTER)
for relative in RELATIVE_FILES:
    live = PERFETTO / relative
    baseline_hash = hashlib.sha256(git_blob(relative)).hexdigest()
    patched_hash = inventory.sha256_file(AFTER / "third_party/perfetto" / relative)
    if inventory.sha256_file(live) not in (baseline_hash, patched_hash):
        raise RuntimeError("live source differs from the pinned baseline and patch: " + str(live))

FIXTURE = PORTS / "probes/electron/tests/perfetto-murmur-gcc16.cpp"
if not FIXTURE.is_file():
    raise RuntimeError("missing Murmur golden-vector fixture")


def run_murmur(overlay, tag):
    binary = OBJECTS / (tag + "-murmur-test")
    argv = [HOST_CXX, "-std=c++17", "-Wall", "-Wextra", "-Werror",
            "-isysroot", HOST_SDK,
            "-I", overlay / "third_party/perfetto/include",
            "-I", OUT / "gen/third_party/perfetto/build_config",
            "-I", OUT / "gen/third_party/perfetto",
            "-I", PERFETTO / "include", "-I", SOURCE,
            FIXTURE, "-o", binary]
    row, _ = invoke(tag + "-murmur-build", argv, expected=0)
    row2, stderr = invoke(tag + "-murmur-run", [binary], expected=0)
    return [row, row2]


def production_command(target, source_relative):
    row, _ = invoke("ninja-commands-" + target.rsplit("/", 1)[-1],
                    [NINJA, "-C", OUT, "-t", "commands", target], expected=0)
    lines = (LOGS / (row["name"] + ".stdout")).read_text().splitlines()
    matches = []
    wanted = (SOURCE / source_relative).resolve(strict=True)
    for line in lines:
        try:
            argv = shlex.split(line)
        except ValueError:
            continue
        if "-c" not in argv:
            continue
        source_arg = Path(argv[argv.index("-c") + 1])
        actual = (OUT / source_arg).resolve() if not source_arg.is_absolute() else source_arg
        if actual == wanted:
            matches.append(argv)
    if len(matches) != 1:
        raise RuntimeError("Ninja command database did not return one command for " + str(wanted))
    return matches[0]


MURMUR_SOURCE = Path("third_party/perfetto/src/trace_processor/importers/proto/network_trace_module.cc")
CONSOLE_SOURCE = Path("third_party/perfetto/src/tracing/console_interceptor.cc")
TARGETS = {
    "murmur": "obj/third_party/perfetto/src/trace_processor/importers/proto/minimal/network_trace_module.o",
    "console": "obj/third_party/perfetto/src/tracing/client_api_without_backends/console_interceptor.o",
}


def compile_production(name, overlay, *, expect, diagnostics=()):
    argv = list(COMMANDS[name])
    if Path(argv[0]).resolve(strict=True) != CXX:
        raise RuntimeError(name + " production command does not use --cxx")
    if "-Werror" not in argv:
        raise RuntimeError(name + " production command lost -Werror")
    if not any(arg == "--sysroot=" + str(SYSROOT) for arg in argv):
        if not any(arg == "--sysroot" + str(SYSROOT) for arg in argv):
            raise RuntimeError(name + " production command does not select --sysroot")
    if name == "console":
        source_index = argv.index("-c") + 1
        argv[source_index] = overlay / "third_party/perfetto/src/tracing/console_interceptor.cc"
    else:
        source_index = argv.index("-c") + 1
    if "-MF" in argv:
        argv[argv.index("-MF") + 1] = OBJECTS / (name + "-" + overlay.name + ".d")
    if "-o" not in argv:
        raise RuntimeError(name + " production command has no object output")
    argv[argv.index("-o") + 1] = OBJECTS / (name + "-" + overlay.name + ".o")
    argv.insert(1, "-I" + str(overlay / "third_party/perfetto/include"))
    argv = [str(item) for item in argv]
    result = capture(argv, cwd=OUT)
    (LOGS / (name + "-" + overlay.name + ".stdout")).write_bytes(result.stdout)
    (LOGS / (name + "-" + overlay.name + ".stderr")).write_bytes(result.stderr)
    row = {"name": name + "-" + overlay.name, "argv": argv, "cwd": str(OUT),
           "returncode": result.returncode,
           "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
           "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
           "stdout_bytes": len(result.stdout), "stderr_bytes": len(result.stderr)}
    if result.returncode != expect:
        raise RuntimeError(row["name"] + " returned " + str(result.returncode))
    text = result.stderr.decode(errors="replace")
    for diagnostic in diagnostics:
        if diagnostic not in text:
            raise RuntimeError(row["name"] + " missed expected diagnostic " + diagnostic)
    return row


with process.ContextLocks([str(OUT), str(SYSROOT)], str(LOCK_ROOT), shared=True):
    TEST_ROWS = run_murmur(BEFORE, "before") + run_murmur(AFTER, "after")
    COMMANDS = {
        "murmur": production_command(TARGETS["murmur"], MURMUR_SOURCE),
        "console": production_command(TARGETS["console"], CONSOLE_SOURCE),
    }
    PRODUCTION_ROWS = [
        compile_production("murmur", BEFORE, expect=1,
                           diagnostics=("array-bounds", "-Werror")),
        compile_production("murmur", AFTER, expect=0),
        compile_production("console", BEFORE, expect=1,
                           diagnostics=("format-truncation", "format-overflow")),
        compile_production("console", AFTER, expect=0),
    ]

receipt = {
    "source_revision": source_rev,
    "perfetto_revision": perfetto_rev,
    "gn_args_sha256": inventory.sha256_file(OUT / "args.gn"),
    "ninja_graph_sha256": inventory.sha256_file(OUT / "build.ninja"),
    "patch_sha256": inventory.sha256_file(PATCH),
    "compiler": str(CXX),
    "target": capture([CXX, "-dumpmachine"]).stdout.decode().strip(),
    "host_cxx": str(HOST_CXX),
    "host_sdk": str(HOST_SDK),
    "work_dir": str(WORK),
    "murmur_golden_vectors": 16,
    "production_compile": PRODUCTION_ROWS,
    "host_fixture": TEST_ROWS,
}
jsonio.write_json(WORK / "results.json", receipt)
print(json.dumps(receipt, indent=2, sort_keys=True))
