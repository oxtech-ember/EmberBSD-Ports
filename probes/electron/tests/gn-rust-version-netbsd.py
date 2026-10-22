#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted E12 GN regression).
"""Causally test Chromium's production Rust-version GN defaults."""
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
import stat

parser = argparse.ArgumentParser(description=__doc__)
for name in ("source", "gn", "patch", "sdk-source", "ports-root", "sysroot"):
    parser.add_argument("--" + name, required=True, type=Path)
parser.add_argument("new_work", type=Path, metavar="NEW_WORK")
args = parser.parse_args()
for label, path in (("Chromium source", args.source), ("GN", args.gn),
                    ("patch", args.patch), ("SDK source", args.sdk_source),
                    ("Ports root", args.ports_root), ("sysroot", args.sysroot),
                    ("NEW_WORK", args.new_work)):
    if not path.is_absolute():
        parser.error(f"{label} must be absolute")
SOURCE, GN, PATCH, SDK_SOURCE, PORTS, SYSROOT = (
    path.resolve(strict=True) for path in
    (args.source, args.gn, args.patch, args.sdk_source,
     args.ports_root, args.sysroot))
ROOT = args.new_work.resolve()
for label, boundary in (("Chromium source", SOURCE), ("SDK source", SDK_SOURCE),
                        ("Ports root", PORTS), ("sysroot", SYSROOT)):
    if ROOT.is_relative_to(boundary) or boundary.is_relative_to(ROOT):
        parser.error(f"NEW_WORK must be disjoint from {label}")
if ROOT.exists():
    parser.error("NEW_WORK must be a new directory")
if not ROOT.parent.is_dir():
    parser.error("NEW_WORK parent must exist")

SDK_PACKAGE = SDK_SOURCE / "src/emberbsd_sdk"
if not (SDK_PACKAGE / "__init__.py").is_file():
    parser.error("selected SDK source has no emberbsd_sdk API")
sys.path.insert(0, str(SDK_SOURCE / "src"))
import emberbsd_sdk
if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error("selected SDK must provide API version 1")
if Path(emberbsd_sdk.__file__).resolve().parent != SDK_PACKAGE.resolve():
    parser.error("emberbsd_sdk must come from the selected SDK source")
from emberbsd_sdk import errors, inventory, jsonio, process
SDK_MODULES = (emberbsd_sdk, errors, inventory, jsonio, process)
if any(not Path(module.__file__).resolve().is_relative_to(SDK_PACKAGE.resolve())
       for module in SDK_MODULES):
    parser.error("all imported SDK modules must come from selected SDK source")
CommandError = errors.CommandError
capture = process.capture
sha256_file = inventory.sha256_file
write_json = jsonio.write_json

RUST_GNI = SOURCE / "build/config/rust.gni"
RUN_BINARY = SOURCE / "build/gn_run_binary.py"
if not RUST_GNI.is_file() or not RUN_BINARY.is_file():
    parser.error("Chromium source is missing production Rust GN inputs")
if not os.access(GN, os.X_OK):
    parser.error("selected GN executable is not executable")
PATCH_TEXT = PATCH.read_text()
if "/Users/" in PATCH_TEXT or "/Volumes/" in PATCH_TEXT:
    parser.error("candidate patch must not contain machine-local paths")
if "build/config/rust.gni" not in PATCH_TEXT:
    parser.error("candidate patch must modify build/config/rust.gni")
patch_headers = [line for line in PATCH_TEXT.splitlines()
                 if line.startswith(("--- ", "+++ "))]
if patch_headers != ["--- a/build/config/rust.gni",
                     "+++ b/build/config/rust.gni"]:
    parser.error("candidate patch must touch only build/config/rust.gni")
patch_bin = shutil.which("patch", path=process.sanitized_environment().get("PATH"))
if patch_bin is None:
    parser.error("base-system patch utility is required")
PATCH_BIN = Path(patch_bin).resolve(strict=True)

ROOT.mkdir()
LOGS = ROOT / "logs"
LOGS.mkdir()
SOURCE_INPUTS = (RUST_GNI, RUN_BINARY, GN, PATCH, PATCH_BIN)
source_hashes_before = {str(path): sha256_file(path) for path in SOURCE_INPUTS}
source_modes_before = {str(path): stat.S_IMODE(path.stat().st_mode) for path in SOURCE_INPUTS}
commands = []

def record(name, argv, cwd, env):
    try:
        result = capture(list(map(str, argv)), cwd=cwd, env=env)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except CommandError as error:
        code, stdout, stderr = error.returncode, error.stdout, error.stderr
    (LOGS / (name + ".stdout")).write_bytes(stdout)
    (LOGS / (name + ".stderr")).write_bytes(stderr)
    commands.append({"name": name, "argv": list(map(str, argv)),
                     "cwd": str(cwd), "returncode": code})
    write_json(ROOT / "commands.json", commands, exclusive=False)
    return code, stdout, stderr


def patch_trial(name, *, reverse=False, dry_run=False):
    """Apply/check the carried patch against a disposable production-file copy."""
    tree = ROOT / name
    target = tree / "build/config/rust.gni"
    target.parent.mkdir(parents=True)
    shutil.copy2(RUST_GNI, target)
    argv = [PATCH_BIN]
    if reverse:
        argv.append("-R")
    argv += ["--forward", "--dry-run" if dry_run else "--batch",
             "-p1", "-F0", "-i", PATCH]
    code, stdout, stderr = record(name, argv, tree,
                                  process.sanitized_environment())
    return code, stdout, stderr, target.read_bytes()


forward_check = patch_trial("source-patch-forward-check", dry_run=True)
reverse_check = patch_trial("source-patch-reverse-check", reverse=True,
                            dry_run=True)
if (forward_check[0] == 0) == (reverse_check[0] == 0):
    raise RuntimeError("source rust.gni must match exactly one patch state; "
                       "neither or both strict -F0 checks passed")
if forward_check[0] == 0:
    source_patch_state = "baseline"
    baseline_gni = RUST_GNI.read_bytes()
    patched_result = patch_trial("stage-patched-source", dry_run=False)
    if patched_result[0] != 0:
        raise RuntimeError("could not create patched fixture source: "
                           + (patched_result[1] + patched_result[2]).decode(
                               "utf-8", "replace"))
    patched_gni = patched_result[3]
else:
    source_patch_state = "patched"
    patched_gni = RUST_GNI.read_bytes()
    baseline_result = patch_trial("stage-baseline-source", reverse=True,
                                  dry_run=False)
    if baseline_result[0] != 0:
        raise RuntimeError("could not reconstruct baseline fixture source: "
                           + (baseline_result[1] + baseline_result[2]).decode(
                               "utf-8", "replace"))
    baseline_gni = baseline_result[3]

BASE_CONFIG = r'''declare_args() {
  fixture_host_os = "mac"
  fixture_target_os = "netbsd"
  fixture_target_cpu = "arm64"
}
build_with_chromium = false
is_wasm = false
is_android = false
is_ios = false
is_linux = fixture_target_os == "linux"
is_chromeos = false
is_fuchsia = false
is_mac = fixture_target_os == "mac"
is_win = false
is_apple = false
is_bsd = fixture_target_os == "netbsd"
host_os = fixture_host_os
target_os = fixture_target_os
host_cpu = "arm64"
target_cpu = fixture_target_cpu
current_os = target_os
current_cpu = target_cpu
host_toolchain = "//toolchain:host"
current_toolchain = "//toolchain:default"
toolchain_for_rust_host_build_tools = false
import("//build/config/rust.gni")
set_default_toolchain("//toolchain:default")
'''
TOOLCHAINS = r'''toolchain("default") {
  tool("stamp") { command = "touch {{output}}" }
}
toolchain("host") {
  tool("stamp") { command = "touch {{output}}" }
}
'''
BUILD = r'''group("probe") {
  metadata = {
    rustc_revision = [ rustc_revision ]
  }
}
'''


def make_fixture(name, *, rust_gni_bytes, host_os="mac", target_os="netbsd"):
    tree = ROOT / name
    tree.mkdir()
    for relative in ("build/config/compiler", "build/config/sanitizers",
                     "build/toolchain", "build/rust", "toolchain",
                     "third_party/rust-toolchain"):
        (tree / relative).mkdir(parents=True, exist_ok=True)
    (tree / ".gn").write_text(
        'buildconfig = "//fixture_config.gn"\nscript_executable = '
        + json.dumps(sys.executable) + "\n")
    config = BASE_CONFIG.replace('fixture_host_os = "mac"',
                                 'fixture_host_os = ' + json.dumps(host_os))
    config = config.replace('fixture_target_os = "netbsd"',
                            'fixture_target_os = ' + json.dumps(target_os))
    (tree / "fixture_config.gn").write_text(config)
    rust_gni = tree / "build/config/rust.gni"
    rust_gni.write_bytes(rust_gni_bytes)
    shutil.copy2(RUN_BINARY, tree / "build/gn_run_binary.py")
    for stub in ("build/config/chrome_build.gni",
                 "build/config/compiler/compiler.gni",
                 "build/config/sanitizers/sanitizers.gni",
                 "build/toolchain/toolchain.gni"):
        (tree / stub).write_text("# fixture import stub\n")
    (tree / "toolchain/BUILD.gn").write_text(TOOLCHAINS)
    (tree / "BUILD.gn").write_text(BUILD)
    (tree / "build/rust/known-target-triples.txt").write_text(
        "aarch64-unknown-linux-gnu\n")
    (tree / "third_party/rust-toolchain/VERSION").write_text(
        "rustc 1.88.0 a1b2c3d4 (a1b2c3d4-1-llvmorg-23-init-0 chromium)\n")
    return tree


def generate(name, *, rust_gni_bytes, host_os="mac", target_os="netbsd",
             rustc_version=None, fake_rustc=False,
             rust_sysroot="/fixture/custom-rust-sysroot"):
    tree = make_fixture(name, rust_gni_bytes=rust_gni_bytes, host_os=host_os,
                        target_os=target_os)
    out = tree / "out/default"
    out.mkdir(parents=True)
    if fake_rustc:
        marker = tree / "rustc-invoked.log"
        script = ("#!/bin/sh\n"
                  f"printf '%s\\n' \"$*\" >> {json.dumps(str(marker))}\n"
                  "printf '%s\\n' 'rustc 1.85.0 (fixture)'\n")
        executable = out / "rustc"
        executable.write_text(script)
        executable.chmod(0o755)
    args_gn = {
        "enable_rust": True,
        "rust_sysroot_absolute": rust_sysroot,
    }
    if rustc_version is not None:
        args_gn["rustc_version"] = rustc_version
    (out / "args.gn").write_text("\n".join(
        key + " = " + json.dumps(value) for key, value in args_gn.items()) + "\n")
    env = process.sanitized_environment()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    code, stdout, stderr = record(name + "-gn-gen",
        [GN, "gen", out, "--root=" + str(tree)], tree, env)
    return tree, out, code, stdout, stderr


def expect(condition, message):
    if not condition:
        raise AssertionError(message)

# Record the selected generator before building fixtures.
gn_status, gn_stdout, gn_stderr = record(
    "gn-version", [GN, "--version"], ROOT, process.sanitized_environment())
expect(gn_status == 0, "cannot query selected GN version")
gn_version = (gn_stdout + gn_stderr).decode("utf-8", "replace").strip()

# Reproduce the original failure: args.gn supplies a version, but GN still
# evaluates the old exec_script default and has no ./rustc in this cross tree.
baseline_tree, baseline_out, baseline_code, baseline_stdout, baseline_stderr = generate(
    "baseline-cross", rust_gni_bytes=baseline_gni,
    rustc_version="rustc 1.88.0 (fixture)")
expect(baseline_code != 0, "baseline must fail when the unconditional rustc probe has no ./rustc")
expect(b"rustc" in baseline_stdout.lower() + baseline_stderr.lower(),
       "baseline failure must identify the attempted rustc probe")
expect(not (baseline_tree / "rustc-invoked.log").exists(),
       "baseline must not invent or run a fake rustc")

# With the patch, an explicit version avoids the host binary and cross GN passes.
cross_tree, cross_out, cross_code, cross_stdout, cross_stderr = generate(
    "patched-cross", rust_gni_bytes=patched_gni,
    rustc_version="rustc 1.88.0 (fixture)")
expect(cross_code == 0, "NetBSD cross GN must pass with an explicit rustc_version: "
       + (cross_stdout + cross_stderr).decode("utf-8", "replace"))
expect(not (cross_tree / "rustc-invoked.log").exists(),
       "NetBSD cross GN must not invoke a host rustc")
code, desc_out, desc_err = record("patched-cross-metadata",
    [GN, "desc", cross_out, "//:probe", "metadata", "--format=json"], cross_tree,
    process.sanitized_environment())
expect(code == 0, "GN metadata query must pass: "
       + (desc_out + desc_err).decode("utf-8", "replace"))
metadata = json.loads(desc_out)
expect("1880-fixture" in json.dumps(metadata),
       "GN must consume and normalize the explicitly supplied pinned version")

# Missing version is rejected by the explicit custom-sysroot contract.
missing_tree, missing_out, missing_code, missing_stdout, missing_stderr = generate(
    "patched-cross-missing-version", rust_gni_bytes=patched_gni)
missing_text = (missing_stdout + missing_stderr).decode("utf-8", "replace")
expect(missing_code != 0, "NetBSD cross GN must reject a missing rustc_version")
expect("requires rustc_version" in missing_text,
       "missing-version failure must name the required GN input")
expect(not (missing_tree / "rustc-invoked.log").exists(),
       "missing-version validation must not invoke a host rustc")

# The in-tree Chromium Rust toolchain does not need rustc_version; it reads its
# pinned VERSION file and must also avoid probing a cross host rustc.
bundled_tree, bundled_out, bundled_code, bundled_stdout, bundled_stderr = generate(
    "patched-cross-bundled-toolchain", rust_gni_bytes=patched_gni,
    rust_sysroot="")
bundled_text = (bundled_stdout + bundled_stderr).decode("utf-8", "replace")
expect(bundled_code == 0, "bundled NetBSD cross GN must pass without rustc_version: "
       + bundled_text)
expect(not (bundled_tree / "rustc-invoked.log").exists(),
       "bundled NetBSD cross GN must not invoke a host rustc")

# Native NetBSD and unrelated host/target OS keep the old rustc -V fallback.
fallback_invocations = {}
for name, host, target in (("native-netbsd", "netbsd", "netbsd"),
                           ("unrelated-linux-cross", "mac", "linux")):
    tree, out, code, stdout, stderr = generate(name,
        rust_gni_bytes=patched_gni, host_os=host, target_os=target,
        fake_rustc=True)
    text = (stdout + stderr).decode("utf-8", "replace")
    expect(code == 0, name + " GN fallback failed: " + text)
    marker = tree / "rustc-invoked.log"
    expect(marker.is_file(), name + " must retain the rustc -V fallback")
    invocations = marker.read_text().splitlines()
    expect(invocations and set(invocations) == {"-V"},
           name + " fallback must invoke rustc only with -V")
    fallback_invocations[name] = invocations

source_hashes_after = {str(path): sha256_file(path) for path in SOURCE_INPUTS}
source_modes_after = {str(path): stat.S_IMODE(path.stat().st_mode) for path in SOURCE_INPUTS}
expect(source_hashes_before == source_hashes_after,
       "source, patch, GN, SDK, or base patch tool changed during the test")
expect(source_modes_before == source_modes_after,
       "an input mode changed during the test")

receipt = {
    "schema": 1,
    "chromium_source_root": str(SOURCE),
    "rust_gni_sha256": source_hashes_before[str(RUST_GNI)],
    "gn_run_binary_sha256": source_hashes_before[str(RUN_BINARY)],
    "candidate_patch": str(PATCH),
    "candidate_patch_sha256": source_hashes_before[str(PATCH)],
    "source_patch_state": source_patch_state,
    "baseline_fixture_rust_gni_sha256": hashlib.sha256(baseline_gni).hexdigest(),
    "patched_fixture_rust_gni_sha256": hashlib.sha256(patched_gni).hexdigest(),
    "gn": str(GN),
    "gn_sha256": source_hashes_before[str(GN)],
    "gn_version": gn_version,
    "python": sys.executable,
    "python_version": sys.version,
    "sdk_source": str(SDK_SOURCE),
    "sdk_api": 1,
    "sdk_modules": {str(Path(module.__file__).resolve()): sha256_file(Path(module.__file__).resolve())
                     for module in SDK_MODULES},
    "sysroot_boundary": str(SYSROOT),
    "ports_boundary": str(PORTS),
    "cases": {
        "baseline_cross_with_explicit_version": "expected failure: unconditional host rustc probe",
        "patched_cross_with_explicit_version": "pass; exact supplied rustc_revision observed; no rustc invocation",
        "patched_cross_missing_version": "expected failure: explicit missing-input assertion",
        "patched_cross_bundled_toolchain": "pass; pinned in-tree VERSION used without probing rustc",
        "native_netbsd": "pass; default rustc -V fallback retained",
        "unrelated_linux_cross": "pass; default rustc -V fallback retained",
    },
    "fallback_invocations": fallback_invocations,
    "commands": commands,
    "source_input_sha256_before": source_hashes_before,
    "source_input_sha256_after": source_hashes_after,
    "source_modes_before": source_modes_before,
    "source_modes_after": source_modes_after,
}
write_json(ROOT / "receipt.json", receipt)
print("PASS: strict patch-state detection and production Rust GN baseline/patched fixtures")
print("source patch state: " + source_patch_state)
print("receipt: " + str(ROOT / "receipt.json"))
