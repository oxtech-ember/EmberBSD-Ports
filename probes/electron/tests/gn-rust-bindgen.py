#!/usr/bin/env python3.15
# Origin: EmberBSD (AI-assisted). Regression for Chromium's production Rust bindgen GN templates.
"""Check pinned bindgen paths and target-only EmberBSD clang sysroot arguments."""
import sys
sys.dont_write_bytecode = True
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("use the selected host CPython 3.15")

import argparse
import json
import os
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
for name in ("source", "gn", "bindgen", "rustfmt", "sdk-source", "sysroot", "patch"):
    parser.add_argument("--" + name, required=True, type=Path)
parser.add_argument("new_work", type=Path, metavar="NEW_WORK")
args = parser.parse_args()
if not args.sdk_source.is_absolute() or not args.new_work.is_absolute():
    parser.error("SDK source and NEW_WORK must be absolute paths")
SDK_SOURCE = args.sdk_source.resolve(strict=True)
package = SDK_SOURCE / "src/emberbsd_sdk"
if not (package / "__init__.py").is_file():
    parser.error("selected SDK source has no emberbsd_sdk API")
sys.path.insert(0, str(SDK_SOURCE / "src"))
import emberbsd_sdk
if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error("selected SDK must provide API version 1")
if Path(emberbsd_sdk.__file__).resolve().parent != package.resolve():
    parser.error("SDK package must come from selected source")
from emberbsd_sdk import errors, inventory, jsonio, process
SDK_MODULES = (emberbsd_sdk, errors, inventory, jsonio, process)
if any(not Path(module.__file__).resolve().is_relative_to(package.resolve()) for module in SDK_MODULES):
    parser.error("SDK modules must come from selected source")
CommandError = errors.CommandError
capture = process.capture
sha256_file = inventory.sha256_file
write_json = jsonio.write_json
SOURCE, GN, BINDGEN, RUSTFMT = (p.resolve(strict=True) for p in
    (args.source, args.gn, args.bindgen, args.rustfmt))
SYSROOT = args.sysroot.resolve(strict=True)
ROOT = args.new_work.resolve()
if ROOT.is_relative_to(SOURCE):
    parser.error("NEW_WORK must be outside Chromium source")
ROOT.mkdir(parents=True)
LOGS = ROOT / "logs"
LOGS.mkdir()
PATCH = args.patch.resolve(strict=True)
GENERATOR = Path("build/rust/rust_bindgen_generator.gni")
WRAPPER = Path("build/rust/rust_bindgen.gni")

# Minimal GN root. The two production templates are copied byte-for-byte; the
# imported Chromium configuration files are replaced with minimal fixture stubs.
BUILDCONFIG = r'''declare_args() {
  fixture_host_os = "mac"
  fixture_host_cpu = "arm64"
  fixture_target_os = "netbsd"
  fixture_target_cpu = "arm64"
  rust_bindgen_root = "//custom/rust-toolchain"
  emberbsd_target_sysroot = "/fixture/emberbsd-sysroot"
}
host_os = fixture_host_os
host_cpu = fixture_host_cpu
target_os = fixture_target_os
target_cpu = fixture_target_cpu
if (current_os == "") { current_os = target_os }
if (current_cpu == "") { current_cpu = target_cpu }
host_toolchain = "//toolchain:host"
set_default_toolchain("//toolchain:default")
# Match Chromium's target predicate for the two fixture toolchains. Native
# host/target equality is also guarded below by the OS/CPU difference check.
is_a_target_toolchain = current_os == target_os && current_cpu == target_cpu
is_linux = current_os == "linux"
is_win = false
is_cfi = false
use_chromium_rust_toolchain = true
rust_sysroot_absolute = "//fixture-rust-sysroot"
clang_base_path = "//fixture-clang"
clang_version = "23"
default_compiler_configs = [ "//build/config/compiler:tot_warnings" ]
TESTONLY_AND_VISIBILITY = [ "testonly", "visibility" ]
'''
TOOLCHAINS = r'''toolchain("default") {
  tool("stamp") {
    command = "touch {{output}}"
  }
  toolchain_args = {
    current_os = target_os
    current_cpu = target_cpu
  }
}
toolchain("host") {
  tool("stamp") {
    command = "touch {{output}}"
  }
  toolchain_args = {
    current_os = host_os
    current_cpu = host_cpu
  }
}
'''
BUILD = r'''import("//build/rust/rust_bindgen_generator.gni")
rust_bindgen_generator("direct") { header = "//third_party/fixture/probe.h" }
group("all") {
  deps = [
    ":direct",
    ":direct(//toolchain:host)",
  ]
}
'''
ROOT_BUILD = 'group("all") { deps = [ "//third_party/fixture:all" ] }\n'

# Substitute just the import declarations in the production templates so the
# fixture avoids Chromium's broad build graph. All action/template logic remains
# the exact source text under test.
def fixture_tree(version):
    tree = ROOT / version
    for rel in ("build/rust", "build/config/clang", "build/config/compiler", "build/config", "build/toolchain", "toolchain", "third_party/fixture", "custom/rust-toolchain/bin", "custom/rust-toolchain/lib", "fixture-clang/lib/clang/23/include"):
        (tree / rel).mkdir(parents=True, exist_ok=True)
    (tree / ".gn").write_text('buildconfig = "//fixture_config.gn"\nscript_executable = ' + json.dumps(sys.executable) + "\n")
    (tree / "fixture_config.gn").write_text(BUILDCONFIG)
    (tree / "toolchain/BUILD.gn").write_text(TOOLCHAINS)
    (tree / "BUILD.gn").write_text(ROOT_BUILD)
    (tree / "build/config/clang/clang.gni").write_text("# fixture stub\n")
    (tree / "build/config/compiler/BUILD.gn").write_text('config("tot_warnings") {}\n')
    (tree / "build/config/sysroot.gni").write_text("# fixture stub\n")
    (tree / "build/config/rust.gni").write_text("# rust_bindgen_root is declared by fixture_config.gn\n")
    (tree / "build/rust/rust_static_library.gni").write_text('''template("rust_static_library") {
  if (defined(allow_unsafe)) { assert(allow_unsafe) }
  if (defined(crate_name)) { assert(crate_name != "") }
  if (defined(crate_root)) { assert(crate_root != "") }
  if (defined(rustflags)) { assert(rustflags != []) }
  if (defined(no_allocator_crate)) { assert(no_allocator_crate) }
  if (defined(no_chromium_prelude)) { assert(no_chromium_prelude) }
  if (defined(no_clippy)) { assert(no_clippy) }
  group(target_name) { forward_variables_from(invoker, TESTONLY_AND_VISIBILITY + [ "deps" ]) }
}
''')
    (tree / "third_party/fixture/BUILD.gn").write_text(BUILD)
    (tree / "third_party/fixture/probe.h").write_text("typedef struct e12_probe { unsigned int value; } e12_probe;\nint e12_probe_add(int value);\n")
    (tree / "custom/rust-toolchain/bin/bindgen").write_text("fixture pinned bindgen\n")
    (tree / "custom/rust-toolchain/bin/rustfmt").write_text("fixture pinned rustfmt\n")
    (tree / "custom/rust-toolchain/lib/libclang.dylib").write_text("fixture libclang path\n")
    (tree / "fixture-clang/lib/clang/23/include/.keep").write_text("")
    for rel in (GENERATOR, WRAPPER):
        text = source_templates[rel]
        (tree / rel).write_text(text)
    transition = (version == "before" and source_is_patched) or (version == "after" and not source_is_patched)
    if transition:
        argv = ["/usr/bin/patch"]
        if version == "before":
            argv.append("-R")
        argv.extend(["-p1", "-F0", "-i", str(PATCH)])
        result = capture(argv, cwd=tree,
                         env=process.sanitized_environment())
        (LOGS / f"patch-{version}.stdout").write_bytes(result.stdout)
        (LOGS / f"patch-{version}.stderr").write_bytes(result.stderr)
    return tree

commands = []
def run(name, argv, cwd, env):
    try:
        result = capture(list(map(str, argv)), cwd=cwd, env=env)
    except CommandError as error:
        result = error
    (LOGS / (name + ".stdout")).write_bytes(result.stdout)
    (LOGS / (name + ".stderr")).write_bytes(result.stderr)
    commands.append(dict(name=name, argv=list(map(str, argv)), cwd=str(cwd), status=result.returncode))
    write_json(ROOT / "commands.json", commands, exclusive=False)
    return result

# Each output tree is generated independently from the same small production
# target graph. GN emits metadata only; no Ninja or compiler action runs.
observations = {}
env = process.sanitized_environment()
env["PYTHONDONTWRITEBYTECODE"] = "1"
# Record hashes before GN executes. The test works only in NEW_WORK and must
# leave every source-side input byte-for-byte unchanged.
source_files = (GENERATOR, WRAPPER)
source_hash_before = {p: sha256_file(SOURCE / p) for p in source_files}
head = capture(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], env=env).stdout.decode().strip()
capture(["git", "-C", str(SOURCE), "diff", "--quiet", "--", *map(str, source_files)], env=env)
capture(["git", "-C", str(SOURCE), "diff", "--cached", "--quiet", "--", *map(str, source_files)], env=env)
source_templates = {rel: (SOURCE / rel).read_text() for rel in source_files}
source_is_patched = (
    '_bindgen_path = "${rust_bindgen_root}/bin/bindgen"' in source_templates[GENERATOR]
    and '_rustfmt_path = "${rust_bindgen_root}/bin/rustfmt"' in source_templates[GENERATOR]
    and "_libclang_path = rust_bindgen_root" in source_templates[GENERATOR]
    and "if (is_a_target_toolchain && current_os == \"netbsd\" &&" in source_templates[GENERATOR]
    and '_bindgen_path = "${rust_bindgen_root}/bin/bindgen"' in source_templates[WRAPPER]
    and "_libclang_path = rust_bindgen_root" in source_templates[WRAPPER]
)
source_is_base = (
    '_bindgen_path = "bindgen"' in source_templates[GENERATOR]
    and '_rustfmt_path = "rustfmt"' in source_templates[GENERATOR]
    and '_libclang_path = "clang_base_path"' in source_templates[GENERATOR]
    and 'if (emberbsd_target_sysroot != "") {' in source_templates[GENERATOR]
    and '_bindgen_path = "bindgen"' in source_templates[WRAPPER]
    and '_libclang_path = "/usr/pkg"' in source_templates[WRAPPER]
)
assert source_is_patched != source_is_base, "source must match either the patch input or output"
for version in ("before", "after"):
    tree = fixture_tree(version)
    for case, args_gn in (
        ("cross", 'fixture_host_os = "mac"\nfixture_host_cpu = "arm64"\n'),
        ("native-netbsd", 'fixture_host_os = "netbsd"\nfixture_host_cpu = "arm64"\n'),
        ("linux", 'fixture_target_os = "linux"\nfixture_target_cpu = "arm64"\nfixture_host_os = "mac"\nfixture_host_cpu = "arm64"\n'),
    ):
        output = tree / "out" / case
        output.mkdir(parents=True)
        (output / "args.gn").write_text(args_gn + 'rust_bindgen_root = "//custom/rust-toolchain"\nemberbsd_target_sysroot = "/fixture/emberbsd-sysroot"\n')
        gen = run(version + "-" + case + "-gen", [GN, "gen", output, "--root=" + str(tree)], ROOT, env)
        assert gen.returncode == 0, (version, case, gen.stdout[-3000:], gen.stderr[-3000:])
        for label, host in (("direct", False), ("direct", True)):
            target = "//third_party/fixture:" + label
            if host:
                target += "(//toolchain:host)"
            desc = run(version + "-" + case + "-" + label + ("-host" if host else "-target"),
                       [GN, "desc", output, target, "args", "--format=json"], tree, env)
            assert desc.returncode == 0, (target, desc.stdout, desc.stderr)
            # GN's JSON may be a list (the action args) or an object containing
            # args, depending on pinned GN version; normalize without guessing.
            data = json.loads(desc.stdout)
            if isinstance(data, dict):
                data = data.get("args", data)
            arg_text = "\n".join(map(str, data)) if isinstance(data, list) else json.dumps(data, sort_keys=True)
            observations[(version, case, label, host)] = arg_text

# Confirm the exact regressions are present before, and corrected after.
for case in ("cross", "native-netbsd", "linux"):
    target = observations[("after", case, "direct", False)]
    host = observations[("after", case, "direct", True)]
    assert "custom/rust-toolchain/bin/bindgen" in target
    assert "custom/rust-toolchain/bin/rustfmt" in target
    assert "custom/rust-toolchain" in target and "--libclang-path" in target
    wrapper_before = (ROOT / "before" / WRAPPER).read_text()
    wrapper_after = (ROOT / "after" / WRAPPER).read_text()
    assert '_bindgen_path = "bindgen"' in wrapper_before
    assert '_bindgen_path = "${rust_bindgen_root}/bin/bindgen"' in wrapper_after
    assert '_libclang_path = "/usr/pkg"' in wrapper_before
    assert "_libclang_path = rust_bindgen_root" in wrapper_after
    for actions, host_case in ((target, False), (host, True)):
        wants_ember_sysroot = case == "cross" and not host_case
        if wants_ember_sysroot:
            assert "-isystem/fixture/emberbsd-sysroot/usr/include" in actions
            assert "--target=aarch64-unknown-netbsd" in actions
        else:
            assert "-isystem/fixture/emberbsd-sysroot/usr/include" not in actions
            assert "--target=aarch64-unknown-netbsd" not in actions
    if case == "cross":
        assert "-isystem/fixture/emberbsd-sysroot/usr/include" in observations[("before", case, "direct", True)]
    assert "bindgen" in observations[("before", case, "direct", False)]
    assert "custom/rust-toolchain/bin/bindgen" not in observations[("before", case, "direct", False)]

# Execute only the pinned host bindgen + rustfmt action on a tiny header. The
# target probe uses the configured EmberBSD sysroot/triple, but compiles no
# target object and writes only inside this isolated test root.
smoke = ROOT / "smoke"
smoke.mkdir()
header = smoke / "probe.h"
header.write_text("typedef struct e12_probe { unsigned int value; } e12_probe;\nint e12_probe_add(int value);\n")
run_script = SOURCE / "build/rust/gni_impl/run_bindgen.py"
libclang_dir = SOURCE / "third_party/rust-toolchain/lib"
resource_dir = SOURCE / "third_party/llvm-build/Release+Asserts/lib/clang/23"
assert (libclang_dir / "libclang.dylib").is_file()
assert (resource_dir / "include").is_dir()
for mode in ("host", "target-netbsd-arm64"):
    output = smoke / (mode + ".rs")
    command = [sys.executable, str(run_script), "--bindgen-exe", str(BINDGEN),
               "--rustfmt-exe", str(RUSTFMT), "--header", str(header),
               "--depfile", str(smoke / (mode + ".d")), "--output", str(output),
               "--libclang-path", str(libclang_dir), "--bindgen-flags", "--",
               "-resource-dir", str(resource_dir)]
    if mode.startswith("target-"):
        command.extend(["-isystem" + str(SYSROOT / "usr/include"),
                        "--target=aarch64-unknown-netbsd"])
    command.extend(["-fparse-all-comments", "-fvisibility=default"])
    result = run("bindgen-smoke-" + mode, command, smoke, env)
    assert result.returncode == 0, (mode, result.stdout[-3000:], result.stderr[-3000:])
    generated = output.read_text()
    assert "e12_probe" in generated
    assert output.with_suffix(".d").is_file()

# The source inputs are never modified.
source_hashes = {p: sha256_file(SOURCE / p) for p in source_files}
assert source_hashes == source_hash_before, "test modified the Chromium source tree"
result = dict(status="PASS", cases={"|".join(map(str, key)): value for key, value in observations.items()},
              source_head=head,
              source_sha256={str(k): v for k, v in source_hashes.items()}, patch_sha256=sha256_file(PATCH),
              gn= str(GN), gn_version=run("gn-version", [GN, "--version"], ROOT, env).stdout.decode().strip(),
              sdk_source=str(SDK_SOURCE), sdk_api=1,
              sdk_sha256={str(m.__file__): sha256_file(m.__file__) for m in SDK_MODULES})
write_json(ROOT / "result.json", result)
print(json.dumps(dict(status=result["status"], source_head=result["source_head"],
                      patch_sha256=result["patch_sha256"], gn_version=result["gn_version"],
                      cases=len(observations)), sort_keys=True))
