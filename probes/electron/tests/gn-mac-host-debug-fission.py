#!/usr/bin/env python3.15
"""Causally test Chromium's production mac_toolchain fission override."""
# Origin: AI-assisted EmberBSD regression; not submitted upstream.
# Uses a minimal Apple-template mock; only production mac/BUILD.gn is unmocked.
import sys

sys.dont_write_bytecode = True
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("use the selected host CPython 3.15")

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil

parser = argparse.ArgumentParser(description=__doc__)
for name in ("source", "gn", "patch", "clang", "host-target", "target-cxx",
             "target-sysroot", "target-gcc-lib-version", "target-gcc-lib", "sdk-source"):
    parser.add_argument("--" + name, required=True,
                        type=Path if name not in ("host-target",) else str)
parser.add_argument("new_work", type=Path, metavar="NEW_WORK")
args = parser.parse_args()
if not args.new_work.is_absolute():
    parser.error("NEW_WORK must be absolute")
if not args.sdk_source.is_absolute():
    parser.error("--sdk-source must be absolute")
source = args.source.resolve(strict=True)
(gn, patch, clang, target_cxx, target_sysroot, target_gcc_lib_version, target_gcc_lib) = (
    path.resolve(strict=True) for path in
    (args.gn, args.patch, args.clang, args.target_cxx, args.target_sysroot,
     args.target_gcc_lib_version, args.target_gcc_lib))
sdk_source = args.sdk_source.resolve(strict=True)
sdk_package = sdk_source / "src/emberbsd_sdk"
if not (sdk_package / "__init__.py").is_file():
    parser.error("selected SDK source has no emberbsd_sdk API")
sys.path.insert(0, str(sdk_source / "src"))
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
ports_root = Path(__file__).resolve().parents[3]
protected = (source, sdk_source, target_sysroot, ports_root)
if root.exists() or any(root.is_relative_to(path) or path.is_relative_to(root)
                        for path in protected):
    parser.error("NEW_WORK must be new and disjoint from Chromium, SDK, sysroot, and Ports")
root.mkdir(parents=True)
logs = root / "logs"
logs.mkdir()
commands = []
receipt = root / "receipt.json"
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def run(name, argv, cwd, expected=None):
    argv = list(map(str, argv))
    try:
        result = capture(argv, cwd=cwd, env=environment)
        status, stdout, stderr = result.returncode, result.stdout, result.stderr
    except errors.CommandError as error:
        status, stdout, stderr = error.returncode, error.stdout, error.stderr
    (logs / (name + ".stdout")).write_bytes(stdout)
    (logs / (name + ".stderr")).write_bytes(stderr)
    commands.append({"name": name, "argv": argv, "cwd": str(cwd), "status": status})
    write_json(receipt, {"commands": commands}, exclusive=False)
    if expected is not None and status != expected:
        raise SystemExit(f"{name}: expected status {expected}, got {status}; see logs")
    return status, stdout, stderr


mac_build = source / "build/toolchain/mac/BUILD.gn"
mac_build_sha256 = sha256_file(mac_build)
mac_text = mac_build.read_text(encoding="utf-8")
patch_text = patch.read_text(encoding="utf-8")
if patch_text.count("+++ b/build/toolchain/mac/BUILD.gn") != 1 or \
        patch_text.count('+      if (target_os != "mac") {') != 1 or \
        patch_text.count("+        use_debug_fission = false") != 1:
    raise SystemExit("patch must add the macOS toolchain use_debug_fission override")
if any(marker in patch_text for marker in ("/Volumes/", "/Users/", "/private/tmp/")):
    raise SystemExit("patch contains a host-specific path")
fix_marker = '''      # The cross target can enable split DWARF, but this macOS host toolchain
      # does not emit .dwo files. Keep it on the Apple default.
      if (target_os != "mac") {
        use_debug_fission = false
      }
'''
if mac_text.count(fix_marker) > 1:
    raise SystemExit("source has an ambiguous host debug-fission override")
source_state = "patched" if mac_text.count(fix_marker) == 1 else "unpatched"

# Make exact before/after copies of the production template. Patch application
# and reversal happen only in NEW_WORK, never in the source checkout.
patch_base = root / "patch-check"
patch_build_dir = patch_base / "build/toolchain/mac"
patch_build_dir.mkdir(parents=True)
(patch_build_dir / "BUILD.gn").write_text(mac_text, encoding="utf-8")
git = shutil.which("git") or "git"
if source_state == "patched":
    run("source-patch-reverse-check", [git, "apply", "--reverse", "--check", patch], patch_base, 0)
    run("source-patch-reverse-fixture", [git, "apply", "--reverse", patch], patch_base, 0)
    before_text = (patch_build_dir / "BUILD.gn").read_text(encoding="utf-8")
    after_text = mac_text
else:
    run("source-patch-check", [git, "apply", "--check", patch], patch_base, 0)
    before_text = mac_text
    run("source-patch-fixture", [git, "apply", patch], patch_base, 0)
    after_text = (patch_build_dir / "BUILD.gn").read_text(encoding="utf-8")
if before_text.count(fix_marker) or after_text.count(fix_marker) != 1:
    raise SystemExit("before/after copies do not match the patch states")

APPLE_TOOLCHAIN_STUB = '''# Fixture mock for the imported Apple toolchain interface.
# It forwards the production mac_toolchain invoker arguments unchanged.
template("apple_toolchain") {
  toolchain(target_name) {
    forward_variables_from(invoker, "*", [ "toolchain_args" ])
    toolchain_args = invoker.toolchain_args
    tool("cxx") {
      depfile = "{{output}}.d"
      command = "\\\"$bin_path$host_cxx\\\" --target=$host_target -MD -MF $depfile {{cflags}} -c {{source}} -o {{output}}"
      depsformat = "gcc"
      outputs = [ "{{target_out_dir}}/{{label_name}}/{{source_name_part}}.o" ]
    }
    tool("stamp") {
      command = "touch {{output}}"
    }
  }
}
'''
ROOT_BUILD = '''config("compile_flags") {
  cflags = [ "-g2", "-Werror", "-std=gnu++23" ]
  if (current_os == "mac") {
    cflags += [ "--target=" + host_target ]
  }
  if (use_debug_fission) {
    cflags += [ "-gsplit-dwarf" ]
    c_additional_outputs = [ "{{target_out_dir}}/{{label_name}}/{{source_name_part}}.dwo" ]
  }
}
source_set("host") {
  sources = [ "host.cc" ]
  configs = [ ":compile_flags" ]
}
source_set("target") {
  sources = [ "target.cc" ]
  configs = [ ":compile_flags" ]
}
if (target_os == "netbsd") {
  group("all") {
    deps = [
      ":host(//build/toolchain/mac:clang_arm64)",
      ":target(//:netbsd)",
    ]
  }
} else {
  group("all") {
    deps = [ ":host", ":target" ]
  }
}
if (current_toolchain == default_toolchain && target_os == "netbsd") {
  toolchain("netbsd") {
    toolchain_args = {
      current_os = "netbsd"
      current_cpu = "arm64"
      use_debug_fission = true
    }
    tool("cxx") {
      output = "{{target_out_dir}}/{{label_name}}/{{source_name_part}}.o"
      depfile = "$output.d"
      command = "\\\"$target_cxx\\\" -MD -MF $depfile {{cflags}} --sysroot=\\\"$target_sysroot\\\" -B\\\"$target_gcc_lib_version/\\\" -B\\\"$target_gcc_lib/\\\" -c {{source}} -o $output"
      depsformat = "gcc"
      outputs = [ output ]
    }
    tool("stamp") {
      command = "touch {{output}}"
    }
  }
}
'''
BUILD_CONFIG = '''declare_args() {
  # Fixture policy models Chromium's default only for the tested target OSes.
  use_debug_fission = target_os != "mac"
  is_clang = true
  host_cxx = "clang++"
  target_cxx = "g++"
  host_target = "arm64-apple-macos"
  target_sysroot = ""
  target_gcc_lib_version = ""
  target_gcc_lib = ""
}
host_toolchain = "//build/toolchain/mac:clang_arm64"
if (target_os == "netbsd") {
  set_default_toolchain("//:netbsd")
} else {
  set_default_toolchain("//build/toolchain/mac:clang_arm64")
}
'''


def make_fixture(name, state_text, target_os):
    fixture = root / name
    for relative in (
            "build/toolchain/mac", "build/toolchain/apple", "build/config/mac",
            "build_overrides"):
        (fixture / relative).mkdir(parents=True, exist_ok=True)
    (fixture / ".gn").write_text('buildconfig = "//buildconfig.gn"\n', encoding="utf-8")
    (fixture / "buildconfig.gn").write_text(BUILD_CONFIG, encoding="utf-8")
    (fixture / "build/toolchain/mac/BUILD.gn").write_text(state_text, encoding="utf-8")
    (fixture / "build/toolchain/apple/toolchain.gni").write_text(APPLE_TOOLCHAIN_STUB, encoding="utf-8")
    (fixture / "build/config/mac/mac_sdk.gni").write_text('mac_bin_path = ""\n', encoding="utf-8")
    (fixture / "build/config/v8_target_cpu.gni").write_text(
        'declare_args() { v8_current_cpu = target_cpu }\n', encoding="utf-8")
    (fixture / "build_overrides/build.gni").write_text(
        "# Fixture stub: no build overrides are used by this regression.\n", encoding="utf-8")
    (fixture / "BUILD.gn").write_text(ROOT_BUILD, encoding="utf-8")
    (fixture / "host.cc").write_text(
        'extern "C" int host_smoke(int value) { return value + 3; }\n', encoding="utf-8")
    (fixture / "target.cc").write_text(
        'extern "C" int target_smoke(int value) { return value + 5; }\n', encoding="utf-8")
    out = fixture / "out"
    args_text = " ".join((
        'target_os = ' + json.dumps(target_os),
        'target_cpu = "arm64"',
        "host_cxx = " + json.dumps(str(clang)),
        "target_cxx = " + json.dumps(str(target_cxx)),
        "host_target = " + json.dumps(args.host_target),
        "target_sysroot = " + json.dumps(str(target_sysroot)),
        "target_gcc_lib_version = " + json.dumps(str(target_gcc_lib_version)),
        "target_gcc_lib = " + json.dumps(str(target_gcc_lib)),
    ))
    status, _, _ = run(name + "-gn-gen", [gn, "gen", out, "--root=" + str(fixture),
                                           "--args=" + args_text], root, 0)
    return fixture, out


def generated_edge(out, toolchain_dir, target_name, source_name):
    candidates = [out / toolchain_dir / "obj" / (target_name + ".ninja"),
                  out / "obj" / (target_name + ".ninja")]
    target_file = next((candidate for candidate in candidates if candidate.is_file()), None)
    if target_file is None:
        raise SystemExit(f"could not find generated edge file for {target_name} in {out}")
    text = target_file.read_text(encoding="utf-8")
    match = re.search(r"^build (.+): ([A-Za-z0-9_]+) \.\./" + re.escape(source_name) + r"$",
                      text, re.MULTILINE)
    if match is None:
        raise SystemExit(f"could not find {source_name} compile edge in {target_file}")
    outputs = match.group(1).split()
    rule_name = match.group(2)
    cflags_match = re.search(r"^cflags = (.*)$", text, re.MULTILINE)
    cflags = cflags_match.group(1) if cflags_match else ""
    variables = dict(re.findall(r"^[ \t]*([A-Za-z_][A-Za-z0-9_]*) = (.*)$", text, re.MULTILINE))
    return outputs, cflags, "../" + source_name, variables, rule_name, target_file


def generated_command(out, rule_name, outputs, cflags, source_rel, variables):
    matches = []
    candidates = [out / "toolchain.ninja", *out.glob("*/toolchain.ninja")]
    for toolchain_file in candidates:
        if not toolchain_file.is_file():
            continue
        text = toolchain_file.read_text(encoding="utf-8")
        match = re.search(r"^rule " + re.escape(rule_name) + r"\n((?:^[ \t].*\n)+)",
                          text, re.MULTILINE)
        if match is not None:
            matches.append((toolchain_file, match.group(1)))
    if len(matches) != 1:
        raise SystemExit(f"expected one generated rule {rule_name}, found {len(matches)}")
    toolchain_file, rule_text = matches[0]
    command_match = re.search(r"^  command = (.*)$", rule_text, re.MULTILINE)
    if command_match is None:
        raise SystemExit(f"{rule_name} has no generated command in {toolchain_file}")
    command = command_match.group(1)
    output_text = " ".join(outputs)
    replacements = {
        "${out}.d": output_text + ".d",
        "${out}": output_text,
        "${cflags}": cflags,
        "${in}": source_rel,
    }
    for name, value in variables.items():
        replacements["${" + name + "}"] = value
    for name in sorted(replacements, key=len, reverse=True):
        command = command.replace(name, replacements[name])
    if "${" in command:
        raise SystemExit(f"unexpanded Ninja variable in {rule_name}: {command}")
    return shlex.split(command)


fixtures = {}
for state, text in (("before", before_text), ("after", after_text)):
    for platform in ("cross", "native"):
        target_os = "netbsd" if platform == "cross" else "mac"
        fixtures[(platform, state)] = make_fixture(
            f"fixture-{platform}-{state}", text, target_os)

cross_before, cross_before_out = fixtures[("cross", "before")]
cross_after, cross_after_out = fixtures[("cross", "after")]
native_before, native_before_out = fixtures[("native", "before")]
native_after, native_after_out = fixtures[("native", "after")]

cross_before_host = generated_edge(cross_before_out, "clang_arm64", "host", "host.cc")
cross_after_host = generated_edge(cross_after_out, "clang_arm64", "host", "host.cc")
cross_before_target = generated_edge(cross_before_out, "netbsd", "target", "target.cc")
cross_after_target = generated_edge(cross_after_out, "netbsd", "target", "target.cc")
native_before_host = generated_edge(native_before_out, "clang_arm64", "host", "host.cc")
native_after_host = generated_edge(native_after_out, "clang_arm64", "host", "host.cc")
native_before_target = generated_edge(native_before_out, "clang_arm64", "target", "target.cc")
native_after_target = generated_edge(native_after_out, "clang_arm64", "target", "target.cc")

before_host_outputs, before_host_flags, before_host_source, before_host_vars, before_host_rule, _ = cross_before_host
after_host_outputs, after_host_flags, after_host_source, after_host_vars, after_host_rule, _ = cross_after_host
before_target_outputs, before_target_flags, _, _, _, _ = cross_before_target
after_target_outputs, after_target_flags, after_target_source, after_target_vars, after_target_rule, _ = cross_after_target
native_before_outputs, native_before_flags, _, _, _, _ = native_before_host
native_after_outputs, native_after_flags, native_after_source, native_after_vars, native_after_rule, _ = native_after_host
native_target_before_outputs, native_target_before_flags, _, _, _, _ = native_before_target
native_target_outputs, native_target_flags, _, _, _, _ = native_after_target

if len(before_host_outputs) != 2 or "-gsplit-dwarf" not in before_host_flags:
    raise SystemExit("production mac_toolchain before patch did not inherit target split DWARF")
if len(after_host_outputs) != 1 or "-gsplit-dwarf" in after_host_flags:
    raise SystemExit("production mac_toolchain patch did not remove host split-DWARF outputs")
if before_target_outputs != after_target_outputs or len(after_target_outputs) != 2 or \
        "-gsplit-dwarf" not in before_target_flags or "-gsplit-dwarf" not in after_target_flags:
    raise SystemExit("the NetBSD GCC target lost its split-DWARF output or flag")
if "-Werror" not in after_host_flags or "-Werror" not in after_target_flags:
    raise SystemExit("the fixture lost -Werror")
if native_before_outputs != native_after_outputs or native_before_flags != native_after_flags:
    raise SystemExit("the macOS-native host toolchain changed between patch states")
if "-gsplit-dwarf" in native_after_flags:
    raise SystemExit("native macOS unexpectedly enables split DWARF in this fixture")
if len(native_target_before_outputs) != 1 or len(native_target_outputs) != 1 or \
        native_target_before_flags != native_before_flags or native_target_flags != native_after_flags:
    raise SystemExit("native macOS target defaults changed between patch states")

before_host_cmd = generated_command(cross_before_out, before_host_rule, before_host_outputs,
                                    before_host_flags, before_host_source, before_host_vars)
after_host_cmd = generated_command(cross_after_out, after_host_rule, after_host_outputs,
                                   after_host_flags, after_host_source, after_host_vars)
target_cmd = generated_command(cross_after_out, after_target_rule, after_target_outputs,
                               after_target_flags, after_target_source, after_target_vars)
native_cmd = generated_command(native_after_out, native_after_rule, native_after_outputs,
                               native_after_flags, native_after_source, native_after_vars)

for out_dir, outputs in ((cross_before_out, before_host_outputs),
                         (cross_after_out, after_host_outputs),
                         (cross_before_out, before_target_outputs),
                         (cross_after_out, after_target_outputs),
                         (native_after_out, native_after_outputs),
                         (native_after_out, native_target_outputs)):
    for output in outputs:
        (out_dir / output).parent.mkdir(parents=True, exist_ok=True)

# Run the production-template-generated action that reproduces the original fault.
_, _, before_err = run("cross-host-before-generated-action", before_host_cmd,
                        cross_before_out, 1)
if b".dwo" not in before_err or b".dwo.d" not in before_err:
    raise SystemExit("before-action failed for a reason other than the extra .dwo output")

# Confirm the selected Darwin Clang accepts split-DWARF input but emits no .dwo.
capability_dir = root / "host-split-capability"
capability_dir.mkdir()
capability_src = cross_before / "host.cc"
capability_obj = capability_dir / "capability.o"
capability_dep = capability_dir / "capability.o.d"
capability_cmd = [clang, "--target=" + args.host_target, "-gsplit-dwarf", "-g2", "-Werror",
                  "-MD", "-MF", capability_dep, "-c", capability_src, "-o", capability_obj]
run("host-split-dwarf-capability", capability_cmd, root, 0)
if not capability_obj.is_file() or capability_obj.with_suffix(".dwo").exists():
    raise SystemExit("selected Darwin Clang did not match the observed no-.dwo behavior")

# Compile the production-template-generated fixed host, target, and native actions.
run("cross-host-after-generated-action", after_host_cmd, cross_after_out, 0)
host_obj = cross_after_out / after_host_outputs[0]
host_dep = Path(str(host_obj) + ".d")
if not host_obj.is_file() or not host_dep.is_file() or host_obj.with_suffix(".dwo").exists():
    raise SystemExit("fixed cross-host action did not create only its object and depfile")
run("netbsd-target-after-generated-action", target_cmd, cross_after_out, 0)
target_obj = cross_after_out / after_target_outputs[0]
target_dwo = cross_after_out / after_target_outputs[1]
target_dep = Path(str(target_obj) + ".d")
if not target_obj.is_file() or not target_dep.is_file() or not target_dwo.is_file():
    raise SystemExit("NetBSD GCC action did not create object, depfile, and split-DWARF file")
run("native-macos-after-generated-action", native_cmd, native_after_out, 0)
native_obj = native_after_out / native_after_outputs[0]
native_dep = Path(str(native_obj) + ".d")
if not native_obj.is_file() or not native_dep.is_file() or native_obj.with_suffix(".dwo").exists():
    raise SystemExit("native macOS action did not preserve its ordinary object/depfile behavior")

# Ensure the target's diagnostic policy remains active.
warning_src = root / "warning.cc"
warning_src.write_text('int warning_probe() { int unused = 1; return 0; }\n', encoding="utf-8")
_, _, warning_err = run(
    "target-werror-control",
    [target_cxx, "--sysroot=" + str(target_sysroot),
     "-B" + str(target_gcc_lib_version) + "/", "-B" + str(target_gcc_lib) + "/",
     "-Werror", "-Wunused-variable", "-c", warning_src, "-o", root / "warning.o"],
    root, 1)
if b"error:" not in warning_err:
    raise SystemExit("GCC -Werror control failed without reporting a promoted warning")

file_tool = shutil.which("file")
if file_tool is None:
    raise SystemExit("the host file utility is required to identify compiler outputs")
_, file_out, _ = run("output-file-identification",
                     [file_tool, host_obj, target_obj, target_dwo, native_obj], root, 0)
file_text = file_out.decode("utf-8", errors="replace")
if "Mach-O" not in file_text or "ELF 64-bit" not in file_text or "ARM aarch64" not in file_text:
    raise SystemExit("host/target outputs have unexpected object formats")

artifacts = {}
for path in (host_obj, host_dep, capability_obj, capability_dep, target_obj,
             target_dep, target_dwo, native_obj, native_dep):
    if path.is_file():
        artifacts[str(path.relative_to(root))] = {
            "sha256": sha256_file(path), "size": path.stat().st_size}
if sha256_file(mac_build) != mac_build_sha256:
    raise SystemExit("production mac/BUILD.gn changed during the test")
write_json(receipt, {
    "source_state": source_state,
    "production_mac_build_sha256": mac_build_sha256,
    "production_source_unchanged": True,
    "patch_sha256": sha256_file(patch),
    "fixture_boundary": {
        "production_input": "build/toolchain/mac/BUILD.gn copied byte-for-byte from --source",
        "mocked_input": "Apple apple_toolchain template and unrelated GN imports",
        "global_policy": "use_debug_fission defaults true for NetBSD and false for macOS only",
        "target_policy": "minimal NetBSD toolchain explicitly keeps split-DWARF outputs",
        "compiler_scope": "header-free smoke probes; no Chromium target objects or OUT writes",
    },
    "host_clang_version": run("host-clang-version", [clang, "--version"], root, 0)[1].decode().splitlines()[0],
    "target_gcc_machine": run("target-gcc-machine", [target_cxx, "-dumpmachine"], root, 0)[1].decode().strip(),
    "target_gcc_version": run("target-gcc-version", [target_cxx, "-dumpfullversion", "-dumpversion"], root, 0)[1].decode().strip(),
    "cross_before_host": {"outputs": before_host_outputs, "cflags": before_host_flags},
    "cross_after_host": {"outputs": after_host_outputs, "cflags": after_host_flags},
    "cross_target_before": {"outputs": before_target_outputs, "cflags": before_target_flags},
    "cross_target_after": {"outputs": after_target_outputs, "cflags": after_target_flags},
    "native_mac_before": {"outputs": native_before_outputs, "cflags": native_before_flags},
    "native_mac_after": {"outputs": native_after_outputs, "cflags": native_after_flags},
    "file_output": file_text,
    "artifacts": artifacts,
    "commands": commands,
}, exclusive=False)
print(f"PASS: production mac_toolchain guard is causal; target fission and native macOS are unchanged. Receipt: {receipt}")
