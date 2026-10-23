#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted E12 regression).
"""Reproduce the V8 GCC 16 diagnostics in production compile commands."""
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
               "sysroot", "workspace", "ninja", "patch"):
    parser.add_argument("--" + option, required=True, type=Path)
parser.add_argument("work_dir", type=Path, metavar="NEW_WORK")
args = parser.parse_args()

WORK = args.work_dir
if not WORK.is_absolute() or WORK.exists() or not WORK.parent.is_dir():
    parser.error("NEW_WORK must be a new absolute path under an existing directory")
SDK_SOURCE, PORTS, SOURCE, OUT, CXX, SYSROOT, WORKSPACE, NINJA, PATCH = (
    path.resolve(strict=True) for path in
    (args.sdk_source, args.ports_root, args.source_root, args.gn_out, args.cxx,
     args.sysroot, args.workspace, args.ninja, args.patch)
)
if not all(path.is_dir() for path in
           (PORTS, SOURCE, OUT, SYSROOT, WORKSPACE)):
    parser.error("Ports, Chromium source, GN output, sysroot, and workspace must be directories")
if not all(path.is_file() for path in (CXX, NINJA, PATCH)):
    parser.error("compiler, Ninja, and patch must be files")
if SYSROOT != WORKSPACE / "sysroot" or not (WORKSPACE / "obj").is_dir():
    parser.error("sysroot and SDK lock root must use the canonical workspace layout")
if "target_os = \"netbsd\"" not in (OUT / "args.gn").read_text():
    parser.error("GN args must select the NetBSD target")
if "is_clang = false" not in (OUT / "args.gn").read_text():
    parser.error("GN args must select GCC")
if not (OUT / "build.ninja").is_file():
    parser.error("GN output must contain build.ninja")
for label, root in (("Ports", PORTS), ("Chromium source", SOURCE),
                    ("SDK source", SDK_SOURCE), ("SDK workspace", WORKSPACE),
                    ("sysroot", SYSROOT), ("GN output", OUT)):
    if WORK.is_relative_to(root) or root.is_relative_to(WORK):
        parser.error("NEW_WORK must be separate from " + label)

SDK_PACKAGE = SDK_SOURCE / "src/emberbsd_sdk"
if not (SDK_PACKAGE / "__init__.py").is_file():
    parser.error("--sdk-source must contain src/emberbsd_sdk")
sys.path.insert(0, str(SDK_SOURCE / "src"))
import emberbsd_sdk
from emberbsd_sdk import inventory, jsonio, process
from emberbsd_sdk.errors import CommandError
if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error("selected SDK source must provide integer API version 1")
if Path(emberbsd_sdk.__file__).resolve().parent != SDK_PACKAGE.resolve():
    parser.error("emberbsd_sdk must come from selected SDK source")

SOURCE_PIN = "0f678fa0d9c6e21f26b16c3a6c43aebefc86caaa"
V8 = SOURCE / "v8"
V8_PIN = "d9a012e3"
GIT = shutil.which("git")
PATCH_TOOL = shutil.which("patch")
if not GIT or not PATCH_TOOL:
    parser.error("git and POSIX patch are required")
GIT, PATCH_TOOL = Path(GIT).resolve(strict=True), Path(PATCH_TOOL).resolve(strict=True)

def capture(argv, *, cwd=None):
    try:
        return process.capture([str(value) for value in argv],
                              cwd=str(cwd) if cwd else None,
                              env=process.sanitized_environment())
    except CommandError as exc:
        return exc

def checked_git(*argv):
    result = capture([GIT, "-C", V8, *argv])
    if result.returncode:
        raise RuntimeError("Git command failed: " + " ".join(map(str, argv)))
    return result.stdout

source_rev = capture([GIT, "-C", SOURCE, "rev-parse", "HEAD"]).stdout.decode().strip()
v8_rev = checked_git("rev-parse", "HEAD").decode().strip()
if source_rev != SOURCE_PIN or not v8_rev.startswith(V8_PIN):
    parser.error("Chromium or V8 source revision does not match the regression pin")
if "is_clang = false" not in (OUT / "args.gn").read_text():
    parser.error("GN output does not select GCC")

FILES = (
    Path("src/sandbox/tagged-payload.h"),
    Path("src/common/globals.h"),
    Path("src/bigint/mul-karatsuba.cc"),
    Path("src/heap/heap.h"),
    Path("src/execution/simulator.h"),
)
WORK.mkdir(parents=True, exist_ok=False)
OVERLAYS = {name: WORK / name / "third_party/v8" for name in ("before", "after")}
for name, root in OVERLAYS.items():
    for relative in FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = checked_git("show", v8_rev + ":" + relative.as_posix())
        path.write_bytes(blob)

patch_result = capture([PATCH_TOOL, "-p1", "-F0", "-i", PATCH],
                       cwd=OVERLAYS["after"])
(WORK / "patch.log").write_bytes(patch_result.stdout + patch_result.stderr)
if patch_result.returncode:
    raise RuntimeError("V8 patch did not apply to the pinned source")

def production_command(target, source_path):
    result = capture([NINJA, "-C", OUT, "-t", "commands", target])
    if result.returncode:
        raise RuntimeError("Ninja cannot read command database for " + target)
    matches = []
    wanted = source_path.resolve(strict=True)
    for line in result.stdout.decode(errors="replace").splitlines():
        try:
            argv = shlex.split(line)
        except ValueError:
            continue
        if "-c" not in argv:
            continue
        source_arg = Path(argv[argv.index("-c") + 1])
        actual = (OUT / source_arg).resolve() if not source_arg.is_absolute() else source_arg.resolve()
        if actual == wanted:
            matches.append(argv)
    if len(matches) != 1:
        raise RuntimeError("Ninja did not return one production compile command for " + str(wanted))
    return matches[0]

TARGETS = {
    "tagged-payload": (
        "obj/v8/torque_generated_definitions/embedder-data-array-tq.o",
        OUT / "gen/v8/torque-generated/src/objects/embedder-data-array-tq.cc",
    ),
    "karatsuba": (
        "obj/v8/v8_bigint/mul-karatsuba.o",
        V8 / "src/bigint/mul-karatsuba.cc",
    ),
    "heap-growing-mode": (
        "obj/v8/torque_generated_definitions/js-number-format-tq.o",
        OUT / "gen/v8/torque-generated/src/objects/js-number-format-tq.cc",
    ),
    "nodebug-attribute": (
        "obj/v8/v8_base_without_compiler/api-natives.o",
        V8 / "src/api/api-natives.cc",
    ),
}
COMMANDS = {name: production_command(target, source)
            for name, (target, source) in TARGETS.items()}
OBJECTS, DEPS, LOGS = WORK / "objects", WORK / "deps", WORK / "logs"
for directory in (OBJECTS, DEPS, LOGS):
    directory.mkdir()

def compile_production(name, overlay_name, expected, diagnostics=()):
    argv = list(COMMANDS[name])
    if Path(argv[0]).resolve(strict=True) != CXX:
        raise RuntimeError(name + " production command does not use the selected GCC16")
    if "-Werror" not in argv or not any(
            arg == "--sysroot=" + str(SYSROOT) or arg == "--sysroot" + str(SYSROOT)
            for arg in argv):
        raise RuntimeError(name + " production command lost -Werror or target sysroot")
    overlay = OVERLAYS[overlay_name]
    argv.insert(1, "-I" + str(overlay))
    if name == "karatsuba":
        argv[argv.index("-c") + 1] = str(overlay / "src/bigint/mul-karatsuba.cc")
    if "-MF" in argv:
        argv[argv.index("-MF") + 1] = str(DEPS / (name + "-" + overlay_name + ".d"))
    if "-o" not in argv:
        raise RuntimeError(name + " production command has no object output")
    argv[argv.index("-o") + 1] = str(OBJECTS / (name + "-" + overlay_name + ".o"))
    result = capture(argv, cwd=OUT)
    stdout, stderr = result.stdout, result.stderr
    tag = name + "-" + overlay_name
    (LOGS / (tag + ".stdout")).write_bytes(stdout)
    (LOGS / (tag + ".stderr")).write_bytes(stderr)
    diagnostic_text = stderr.decode(errors="replace")
    if result.returncode != expected:
        raise RuntimeError(tag + " returned " + str(result.returncode))
    for diagnostic in diagnostics:
        if diagnostic not in diagnostic_text:
            raise RuntimeError(tag + " missed expected diagnostic " + diagnostic)
    return {"name": tag, "command": [str(arg) for arg in argv],
            "cwd": str(OUT), "returncode": result.returncode,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "stderr_bytes": len(stderr),
            "object_sha256": inventory.sha256_file(OBJECTS / (tag + ".o"))
            if result.returncode == 0 else None}

with process.ContextLocks([str(OUT), str(SYSROOT)], str(WORKSPACE / "obj"), shared=True):
    rows = [
        compile_production("tagged-payload", "before", 1,
                           ("no matching function for call to", "kPointerTableAddressSpaceName")),
        compile_production("tagged-payload", "after", 0),
        compile_production("karatsuba", "before", 1, ("-Werror=sign-compare",)),
        compile_production("karatsuba", "after", 0),
        compile_production("heap-growing-mode", "before", 1,
                           ("-Werror=changes-meaning",)),
        compile_production("heap-growing-mode", "after", 0),
        compile_production("nodebug-attribute", "before", 1,
                           ("nodebug", "-Werror=attributes")),
        compile_production("nodebug-attribute", "after", 0),
    ]

receipt = {
    "chromium_revision": source_rev,
    "v8_revision": v8_rev,
    "gn_args_sha256": inventory.sha256_file(OUT / "args.gn"),
    "ninja_graph_sha256": inventory.sha256_file(OUT / "build.ninja"),
    "patch_sha256": inventory.sha256_file(PATCH),
    "compiler": str(CXX),
    "target": capture([CXX, "-dumpmachine"]).stdout.decode().strip(),
    "sysroot": str(SYSROOT),
    "work_dir": str(WORK),
    "production_compile": rows,
}
jsonio.write_json(WORK / "results.json", receipt)
print(json.dumps(receipt, indent=2, sort_keys=True))
