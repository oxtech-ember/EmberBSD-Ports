#!/usr/bin/env python3.15
"""Check Chromium GN's Clang resource version against its selected compiler."""
# Origin: EmberBSD (AI-assisted). This inspects host Clang metadata and runs
# minimal GN fixtures. It does not compile or execute target code.
import sys

sys.dont_write_bytecode = True
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("use the selected host CPython 3.15")

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys as _sys

parser = argparse.ArgumentParser(description=__doc__)
for name in ("source", "gn", "sdk-source", "patch"):
    parser.add_argument("--" + name, required=True, type=Path)
parser.add_argument("--clang", type=Path,
                    help="selected pinned Clang; defaults to Chromium's configured clang")
parser.add_argument("new_work", type=Path, metavar="NEW_WORK")
args = parser.parse_args()
if not args.sdk_source.is_absolute() or not args.new_work.is_absolute():
    parser.error("SDK source and NEW_WORK must be absolute paths")
source, gn, patch = (path.resolve(strict=True) for path in
                     (args.source, args.gn, args.patch))
sdk_source = args.sdk_source.resolve(strict=True)
sdk_package = sdk_source / "src/emberbsd_sdk"
if not (sdk_package / "__init__.py").is_file():
    parser.error("selected SDK source has no emberbsd_sdk API")
_sys.path.insert(0, str(sdk_source / "src"))
import emberbsd_sdk
if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error("selected SDK must provide API version 1")
if Path(emberbsd_sdk.__file__).resolve().parent != sdk_package.resolve():
    parser.error("SDK package must come from selected source")
from emberbsd_sdk import errors, inventory, jsonio, process
SDK_MODULES = (emberbsd_sdk, errors, inventory, jsonio, process)
if any(not Path(module.__file__).resolve().is_relative_to(sdk_package.resolve())
       for module in SDK_MODULES):
    parser.error("SDK modules must come from selected source")
capture = process.capture
sha256_file = inventory.sha256_file
write_json = jsonio.write_json

root = args.new_work.resolve()
if root.is_relative_to(source):
    parser.error("NEW_WORK must be outside Chromium source")
root.mkdir(parents=True, exist_ok=False)
logs = root / "logs"
logs.mkdir()

toolchain_file = Path("build/toolchain/toolchain.gni")
toolchain_bytes = (source / toolchain_file).read_bytes()
toolchain_text = toolchain_bytes.decode("utf-8")
branch = '''  } else if (is_apple && host_os == "mac") {
    # EmberBSD cross profile (E12): the macOS host toolchain uses the
    # system Xcode clang, whose resource directory carries its own
    # version (for example clang/21), not the pinned Chromium LLVM.
    clang_version = "21"
'''
if toolchain_text.count(branch) == 1:
    source_state = "unpatched"
elif branch not in toolchain_text and toolchain_text.count('clang_version = "23"') == 1:
    source_state = "patched"
else:
    raise SystemExit("unrecognized build/toolchain/toolchain.gni state")

config_text = (source / "build/config/clang/clang.gni").read_text()
base_match = re.search(r'^default_clang_base_path\s*=\s*"([^"]+)"\s*$',
                       config_text, re.MULTILINE)
if base_match is None:
    raise SystemExit("cannot identify Chromium's default pinned Clang directory")
default_base = base_match.group(1)
if args.clang is None:
    if not default_base.startswith("//"):
        raise SystemExit("configured Clang base is not a Chromium source-relative path")
    clang = (source / default_base[2:] / "bin/clang").resolve(strict=True)
else:
    clang = args.clang.resolve(strict=True)
expected_clang = (source / default_base[2:] / "bin/clang").resolve(strict=True)
if clang != expected_clang:
    raise SystemExit("selected compiler does not match Chromium's configured pinned Clang")
apple_toolchain = (source / "build/toolchain/apple/toolchain.gni").read_text()
if 'prefix = rebase_path("$clang_base_path/bin/", root_build_dir)' not in apple_toolchain or \
        '_cc = "${prefix}clang"' not in apple_toolchain:
    raise SystemExit("Apple toolchain no longer selects clang_base_path/bin/clang")

commands = []
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def run(name, argv, cwd):
    try:
        result = capture(list(map(str, argv)), cwd=cwd, env=environment)
        status, stdout, stderr = result.returncode, result.stdout, result.stderr
    except errors.CommandError as error:
        status, stdout, stderr = error.returncode, error.stdout, error.stderr
    (logs / (name + ".stdout")).write_bytes(stdout)
    (logs / (name + ".stderr")).write_bytes(stderr)
    commands.append(dict(name=name, argv=list(map(str, argv)), cwd=str(cwd), status=status))
    write_json(root / "commands.json", commands, exclusive=False)
    return status, stdout, stderr


resource_status, resource_out, resource_err = run(
    "pinned-clang-resource-dir", [clang, "-print-resource-dir"], source)
if resource_status != 0:
    raise SystemExit("pinned Clang -print-resource-dir failed; see logs")
resource_text = resource_out.decode("utf-8").strip()
if not resource_text or "\n" in resource_text:
    raise SystemExit("pinned Clang returned an invalid resource directory")
resource_dir = Path(resource_text).resolve(strict=True)
resource_version = resource_dir.name
resource_base = resource_dir.parent.parent.parent
if resource_base != expected_clang.parent.parent.resolve():
    raise SystemExit("Clang resource directory is outside its configured pinned toolchain")
header = resource_dir / "include/__stddef_size_t.h"
runtime = resource_dir / "lib/darwin/libclang_rt.osx.a"
if not header.is_file() or not runtime.is_file():
    raise SystemExit("pinned Clang resource directory lacks the required Apple header/runtime")

patch_tool = shutil.which("patch")
if patch_tool is None:
    raise SystemExit("the host patch utility is required to exercise the carried patch")


def write_fixture(label, patched):
    tree = root / label
    (tree / "build/toolchain").mkdir(parents=True)
    (tree / "build/toolchain/toolchain.gni").write_bytes(toolchain_bytes)
    desired = patched != (source_state == "patched")
    if desired:
        reverse = source_state == "patched"
        argv = [patch_tool, "-p1", "-F", "0"]
        if reverse:
            argv.append("-R")
        argv.extend(["-i", str(patch)])
        status, stdout, stderr = run(label + "-apply-patch", argv, tree)
        if status != 0:
            raise SystemExit("cannot apply the carried patch in the isolated fixture")
    text = (tree / toolchain_file).read_text()
    marker = 'clang_version = "21"' in text
    if marker == patched:
        raise SystemExit("fixture patch state does not match its requested variant")
    start_marker = 'declare_args() {\n  if (llvm_force_head_revision) {'
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit("cannot locate the production clang_version declare_args block")
    depth = 0
    end = None
    for offset, character in enumerate(text[start:], start):
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                end = offset + 1
                break
    if end is None:
        raise SystemExit("unterminated clang_version declare_args block")
    (tree / "clang-version.gni").write_text(text[start:end] + "\n")
    (tree / ".gn").write_text(
        'buildconfig = "//fixture_config.gn"\nscript_executable = ' +
        json.dumps(_sys.executable) + "\n")
    (tree / "fixture_config.gn").write_text('''declare_args() {
  fixture_is_apple = true
  fixture_host_os = "mac"
  llvm_force_head_revision = false
}
is_apple = fixture_is_apple
host_os = fixture_host_os
set_default_toolchain("//:default")
''')
    (tree / "BUILD.gn").write_text('''import("//clang-version.gni")
print("E12_CLANG_VERSION=" + clang_version)
toolchain("default") {
  tool("stamp") { command = "touch {{output}}" }
}
group("all") {}
''')
    return tree


before = write_fixture("before", patched=False)
after = write_fixture("after", patched=True)
cases = {
    "mac-host": dict(fixture_is_apple=True, fixture_host_os="mac",
                     llvm_force_head_revision=False, before="21", after=resource_version),
    "netbsd-target": dict(fixture_is_apple=False, fixture_host_os="mac",
                          llvm_force_head_revision=False, before="23", after="23"),
    "forced-head": dict(fixture_is_apple=True, fixture_host_os="mac",
                         llvm_force_head_revision=True, before="24", after="24"),
}
observations = {}
for variant, tree in (("before", before), ("after", after)):
    for name, values in cases.items():
        output = root / variant / "out" / name
        output.mkdir(parents=True)
        (output / "args.gn").write_text("\n".join(
            key + " = " + json.dumps(value) for key, value in values.items()
            if key in ("fixture_is_apple", "fixture_host_os", "llvm_force_head_revision")) + "\n")
        status, stdout, stderr = run(
            variant + "-" + name, [gn, "gen", output, "--root=" + str(tree)], root)
        if status != 0:
            raise SystemExit("GN fixture failed: " + variant + "/" + name)
        match = re.search(rb"E12_CLANG_VERSION=(\d+)", stdout + stderr)
        if match is None:
            raise SystemExit("GN did not report clang_version: " + variant + "/" + name)
        actual = match.group(1).decode("ascii")
        expected = values[variant]
        if actual != expected:
            raise SystemExit(f"{variant}/{name}: expected {expected}, got {actual}")
        observations[variant + "-" + name] = dict(clang_version=actual, expected=expected)

if observations["after-mac-host"]["clang_version"] != resource_version:
    raise SystemExit("patched Apple-host GN version differs from pinned Clang resource version")
if observations["before-mac-host"]["clang_version"] == resource_version:
    raise SystemExit("unpatched GN unexpectedly selects the pinned Clang resource version")
if (expected_clang.parent.parent / "lib/clang/21/lib/darwin/libclang_rt.osx.a").exists():
    raise SystemExit("regression premise changed: the stale Clang 21 runtime now exists")
if (source / toolchain_file).read_bytes() != toolchain_bytes:
    raise SystemExit("source toolchain file changed during the read-only regression")

inputs = (source / toolchain_file, source / "build/config/clang/clang.gni",
          source / "build/toolchain/apple/toolchain.gni", clang, gn, patch)
result = dict(
    status="PASS",
    observations=observations,
    selected_clang=str(clang),
    clang_resource_dir=str(resource_dir),
    clang_resource_version=resource_version,
    resource_header=str(header),
    apple_runtime=str(runtime),
    source_state=source_state,
    input_sha256={str(path): sha256_file(path) for path in inputs},
    sdk_source=str(sdk_source),
    sdk_api=1,
    sdk_sha256={str(module.__file__): sha256_file(module.__file__) for module in SDK_MODULES},
    scope="Six minimal GN evaluations and pinned host Clang metadata query. No compilation, linking, or target execution.")
write_json(root / "result.json", result)
print(json.dumps(dict(status="PASS", gn_cases=len(observations),
                      clang_resource_version=resource_version,
                      result=str(root / "result.json"))))
