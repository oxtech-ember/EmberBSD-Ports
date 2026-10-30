#!/usr/bin/env python3.15
"""Prove the generated NetBSD allocator bindgen action's parser-only flag projection."""
# Origin: EmberBSD (AI-assisted). Runs libclang bindgen only; no compilation.
import sys

sys.dont_write_bytecode = True
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("use the selected host CPython 3.15")

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys as _sys

parser = argparse.ArgumentParser(description=__doc__)
for name in ("source", "out", "sdk-source", "patch"):
    parser.add_argument("--" + name, required=True, type=Path)
parser.add_argument("work", type=Path, metavar="WORK")
args = parser.parse_args()
if not args.sdk_source.is_absolute() or not args.work.is_absolute():
    parser.error("SDK source and WORK must be absolute paths")
source, out, sdk_source, patch = (p.resolve(strict=True) for p in
                                  (args.source, args.out, args.sdk_source, args.patch))
work = args.work.resolve()
if work.is_relative_to(source) or work.is_relative_to(out):
    parser.error("WORK must be outside Chromium source and GN output")
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
work.mkdir(parents=True, exist_ok=False)
logs = work / "logs"
logs.mkdir()

toolchain_ninja = out / "toolchain.ninja"
text = toolchain_ninja.read_text()
rule_marker = "rule __build_rust_allocator_alloc_error_handler_impl_ffi_generator___build_toolchain_linux_unbundle_default__rule\n"
edge_marker = "build gen/build/rust/allocator/alloc_error_handler_impl_ffi_generator/bindings.rs:"
rule_start = text.index(rule_marker)
rule_block = text[rule_start:].split("\n\n", 1)[0]
rule_fields = {}
for line in rule_block.splitlines()[1:]:
    if line.startswith("  ") and " = " in line:
        key, value = line.strip().split(" = ", 1)
        rule_fields[key] = value
edge_start = text.index(edge_marker, rule_start)
edge_block = text[edge_start:].split("\n\n", 1)[0]
edge_fields = {}
for line in edge_block.splitlines()[1:]:
    if line.startswith("  ") and " = " in line:
        key, value = line.strip().split(" = ", 1)
        edge_fields[key] = value
command = rule_fields["command"]
variables = {name: shlex.split(edge_fields[name]) for name in
             ("defines", "include_dirs", "cflags", "cflags_cc")}
action_argv = []
for token in shlex.split(command):
    if token in ("${defines}", "${include_dirs}", "${cflags}", "${cflags_cc}"):
        action_argv.extend(variables[token[2:-1]])
    else:
        action_argv.append(token)
if action_argv[1].endswith("run_bindgen.py") is False:
    raise SystemExit("generated GN action no longer invokes run_bindgen.py")
for option in ("--output", "--depfile"):
    if option not in action_argv:
        raise SystemExit("generated GN action lacks " + option)
raw_clangargs = action_argv[action_argv.index("--") + 1:]
unsupported_warning_flags = [
    "-Wno-maybe-uninitialized",
    "-Wno-packed-not-aligned",
    "-Wno-class-memaccess",
]
gcc_param_flags = [arg for arg in raw_clangargs if arg.startswith("--param=")]

patch_tool = shutil.which("gpatch") or shutil.which("patch")
if patch_tool is None:
    raise SystemExit("the host patch utility is required for isolated before/after fixtures")
filter_relative = Path("build/rust/gni_impl/filter_clang_args.py")
filter_source = source / filter_relative
filter_text = filter_source.read_text()
source_is_patched = "arg.startswith('--param=')" in filter_text


def copy_filter_variant(name, patched):
    tree = work / name
    helpers = tree / "build"
    (helpers / "rust/gni_impl").mkdir(parents=True)
    shutil.copy2(source / "build/rust/gni_impl/run_bindgen.py",
                 helpers / "rust/gni_impl/run_bindgen.py")
    shutil.copy2(source / filter_relative, helpers / "rust/gni_impl/filter_clang_args.py")
    for filename in ("action_helpers.py", "gn_helpers.py"):
        shutil.copy2(source / "build" / filename, helpers / filename)
    desired_matches_source = patched == source_is_patched
    if not desired_matches_source:
        reverse = source_is_patched
        argv = [patch_tool, "-p1", "-F", "0"]
        if reverse:
            argv.append("-R")
        argv.extend(["-i", str(patch)])
        try:
            result = capture(argv, cwd=tree)
        except errors.CommandError as error:
            raise SystemExit("cannot apply patch to isolated " + name + " fixture: " +
                             error.stderr.decode("utf-8", "replace"))
    content = (helpers / "rust/gni_impl/filter_clang_args.py").read_text()
    patched_marker = "arg.startswith('--param=')" in content
    if patched_marker != patched:
        raise SystemExit("isolated filter fixture has the wrong patch state")
    return helpers / "rust/gni_impl/run_bindgen.py", helpers / "rust/gni_impl/filter_clang_args.py"


def load_filter(path):
    spec = importlib.util.spec_from_file_location("fixture_filter_" + path.parent.parent.parent.parent.name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.filter_clang_args


def test_filter_contract(function):
    probe = [
        "-Wall", "-Werror", "-Wconversion", "-Wno-e12-unknown-warning",
        *unsupported_warning_flags, "--param=x=y",
        "--sysroot=/fixture/sysroot", "--target=aarch64-unknown-netbsd",
        "-DABI_PROBE=1", "-Xclang", "-add-plugin", "-ftime-trace",
    ]
    expected = [
        "--sysroot=/fixture/sysroot", "--target=aarch64-unknown-netbsd",
        "-DABI_PROBE=1", "-w", "-Wno-unknown-argument",
        "-Wno-unknown-warning-option", "-Wno-unused-command-line-argument",
    ]
    snapshot = probe[:]
    if function(probe) != expected or probe != snapshot:
        raise SystemExit("filter contract or input immutability failed")


def run_variant(name, patched):
    local_run_bindgen, local_filter = copy_filter_variant(name, patched)
    filter_function = load_filter(local_filter)
    if patched:
        test_filter_contract(filter_function)
    argv = action_argv.copy()
    argv[1] = str(local_run_bindgen)
    for option, value in (("--output", str(work / (name + ".rs")),),
                          ("--depfile", str(work / (name + ".d")),)):
        argv[argv.index(option) + 1] = value
    env = dict(os.environ)
    env.pop("TARGET", None)
    try:
        result = capture(argv, cwd=out, env=env)
        status, stdout, stderr = result.returncode, result.stdout, result.stderr
    except errors.CommandError as error:
        status, stdout, stderr = error.returncode, error.stdout, error.stderr
    (logs / (name + ".stdout")).write_bytes(stdout)
    (logs / (name + ".stderr")).write_bytes(stderr)
    return dict(status=status, stdout=stdout, stderr=stderr,
                output=(work / (name + ".rs")).is_file(),
                depfile=(work / (name + ".d")).is_file(),
                filter_sha256=sha256_file(local_filter), argv=argv,
                run_bindgen=local_run_bindgen, filter_path=local_filter)


before = run_variant("before", patched=False)
after = run_variant("after", patched=True)
before_text = (before["stdout"] + before["stderr"]).decode("utf-8", "replace")
after_text = (after["stdout"] + after["stderr"]).decode("utf-8", "replace")
if after["status"] != 0 or not after["output"] or not after["depfile"]:
    raise SystemExit("patched bindgen parser action did not produce bindings and depfile")

# The same parser projection must leave the actual host-toolchain flag list
# unchanged. The host bindgen action is metadata-only here; it is not rerun.
host_ninja = out / "clang_arm64_for_rust_host_build_tools/toolchain.ninja"
host_text = host_ninja.read_text()
host_rule_marker = "rule __build_rust_allocator_alloc_error_handler_impl_ffi_generator___build_toolchain_mac_clang_arm64_for_rust_host_build_tools__rule\n"
host_edge_marker = "build clang_arm64_for_rust_host_build_tools/gen/build/rust/allocator/alloc_error_handler_impl_ffi_generator/bindings.rs:"
host_rule_start = host_text.index(host_rule_marker)
host_rule_block = host_text[host_rule_start:].split("\n\n", 1)[0]
host_rule_fields = {}
for line in host_rule_block.splitlines()[1:]:
    if line.startswith("  ") and " = " in line:
        key, value = line.strip().split(" = ", 1)
        host_rule_fields[key] = value
host_edge_start = host_text.index(host_edge_marker, host_rule_start)
host_edge_block = host_text[host_edge_start:].split("\n\n", 1)[0]
host_edge_fields = {}
for line in host_edge_block.splitlines()[1:]:
    if line.startswith("  ") and " = " in line:
        key, value = line.strip().split(" = ", 1)
        host_edge_fields[key] = value
host_vars = {name: shlex.split(host_edge_fields[name]) for name in
             ("defines", "include_dirs", "cflags", "cflags_cc")}
host_command_argv = []
for token in shlex.split(host_rule_fields["command"]):
    if token in ("${defines}", "${include_dirs}", "${cflags}", "${cflags_cc}"):
        host_command_argv.extend(host_vars[token[2:-1]])
    else:
        host_command_argv.append(token)
host_clangargs = host_command_argv[host_command_argv.index("--") + 1:]
host_filter_before = load_filter(before["filter_path"])(host_clangargs)
host_filter_after = load_filter(after["filter_path"])(host_clangargs)
if host_filter_before != host_filter_after:
    raise SystemExit("GCC parser fix changes the host-toolchain bindgen argument projection")

# Chromium 156 intentionally filters warning flags in libclang-only parsing.
# Ordinary compiler flags remain outside this projection; verify after GN build.

def file_fact(path):
    return dict(path=str(path), size=path.stat().st_size, sha256=sha256_file(path))

inputs = (toolchain_ninja, filter_source, source / "build/rust/gni_impl/run_bindgen.py",
          source / "build/action_helpers.py", source / "build/gn_helpers.py",
          source / "build/rust/allocator/alloc_error_handler_impl.h", patch, host_ninja)
result = dict(
    status="PASS",
    target=rule_fields.get("description"),
    action=dict(command=command, edge=edge_marker,
                variables={name: edge_fields[name] for name in variables},
                expanded_argv=action_argv),
    source_filter_state="patched" if source_is_patched else "unpatched",
    before=dict(status=before["status"], gcc_param_flags=gcc_param_flags,
                output=before["output"], depfile=before["depfile"],
                stderr=str(logs / "before.stderr")),
    after=dict(status=after["status"], output=after["output"], depfile=after["depfile"],
               stderr=str(logs / "after.stderr")),
    projection=dict(gcc_param_flags=gcc_param_flags,
                    gcc_only_warning_flags=[flag for flag in unsupported_warning_flags if flag in raw_clangargs],
                    gcc_B_flags=[arg for arg in raw_clangargs if arg.startswith("-B")],
                    target_sysroot_flags=[arg for arg in raw_clangargs if arg.startswith("--sysroot")],
                    target_flags=[arg for arg in raw_clangargs if arg.startswith("--target=")],
                    input_has_Werror="-Werror" in raw_clangargs,
                    host_projection_unchanged=host_filter_before == host_filter_after,
                    host_target=host_rule_fields.get("description")),
    input_files=[file_fact(path) for path in inputs],
    output_files=[file_fact(path) for path in
                  (work / "after.rs", work / "after.d")],
    sdk_source=str(sdk_source), sdk_api=1,
    sdk_sha256={str(module.__file__): sha256_file(module.__file__) for module in SDK_MODULES},
    scope="One generated NetBSD target allocator bindgen parser action replayed before and after the exact filter patch. Only WORK outputs were written; no compilation or target execution.")
write_json(work / "result.json", result)
print(json.dumps(dict(status="PASS", target=result["target"],
                      gcc_param_count=len(gcc_param_flags),
                      gcc_B_count=len(result["projection"]["gcc_B_flags"]),
                      result=str(work / "result.json"))))
