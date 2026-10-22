#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Isolated Chromium GN regression.
"""Exercise the NetBSD x64 pkg-config branch with synthetic metadata only."""
import sys
sys.dont_write_bytecode = True
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("use CPython 3.15")
import argparse
import json
import os
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
for name in ("source", "gn", "sdk-source", "patch"):
    parser.add_argument("--" + name, type=Path, required=True)
parser.add_argument("new_work", type=Path)
args = parser.parse_args()
if not args.new_work.is_absolute() or not args.sdk_source.is_absolute():
    parser.error("NEW_WORK and --sdk-source must be absolute")
SOURCE, GN, SDK, PATCH = (p.resolve(strict=True) for p in
                          (args.source, args.gn, args.sdk_source, args.patch))
ROOT = args.new_work.resolve()
if (ROOT.exists() or any(ROOT.is_relative_to(p) or p.is_relative_to(ROOT)
                       for p in (SOURCE, SDK, Path(__file__).resolve().parents[3]))):
    parser.error("NEW_WORK must be a new path disjoint from source, SDK, and Ports")
package = SDK / "src/emberbsd_sdk"
sys.path.insert(0, str(SDK / "src"))
import emberbsd_sdk
if (type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1 or
        Path(emberbsd_sdk.__file__).resolve().parent != package.resolve()):
    parser.error("selected SDK must provide API version 1")
from emberbsd_sdk import errors, inventory, jsonio, process
if any(not Path(m.__file__).resolve().is_relative_to(package.resolve())
       for m in (emberbsd_sdk, errors, inventory, jsonio, process)):
    parser.error("SDK modules must come from selected source")
capture, sha256_file, write_json = process.capture, inventory.sha256_file, jsonio.write_json
CommandError = errors.CommandError
ROOT.mkdir(parents=True)
LOGS = ROOT / "logs"
LOGS.mkdir()
PYTHON = Path(sys.executable).resolve(strict=True)
PKG = Path("build/config/linux/pkg_config.gni")
RUST = Path("build/rust/rust_bindgen_generator.gni")
FILES = (PKG, Path("build/config/linux/pkg-config.py"),
         Path("build/config/compute_inputs_for_analyze.gni"),
         Path("build/config/gclient_args.gni"), Path("build/config/sysroot.gni"),
         Path("build/toolchain/sysroot.gni"), Path("build/toolchain/rbe.gni"),
         Path("build/toolchain/siso.gni"), RUST)
hashes = {str(p): sha256_file(SOURCE / p) for p in FILES}
head = capture(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
               env=process.sanitized_environment()).stdout.decode().strip()
pkg_text, rust_text = [(SOURCE / p).read_text() for p in (PKG, RUST)]
pkg_before = '''_emberbsd_cross_pkg_config =
    host_os == "mac" && current_os == "netbsd" && current_cpu == "arm64" &&
    emberbsd_target_sysroot != ""'''
pkg_after = '''_emberbsd_cross_pkg_config = host_os == "mac" && current_os == "netbsd" &&
                             (current_cpu == "arm64" || current_cpu == "x64") &&
                             emberbsd_target_sysroot != ""'''
rust_before = '''      if (current_os == "netbsd" && current_cpu == "arm64") {
        args += [ "--target=aarch64-unknown-netbsd" ]
      }'''
rust_after = '''      if (current_os == "netbsd" && current_cpu == "arm64") {
        args += [ "--target=aarch64-unknown-netbsd" ]
      } else if (current_os == "netbsd" && current_cpu == "x64") {
        args += [ "--target=x86_64-unknown-netbsd" ]
      }'''
pkg_text = pkg_text.replace(pkg_after, pkg_before) if pkg_after in pkg_text else pkg_text
rust_text = rust_text.replace(rust_after, rust_before) if rust_after in rust_text else rust_text
assert pkg_text.count(pkg_before) == 1 and rust_text.count(rust_before) == 1

mock_root = ROOT / "mock-sysroot"
mock_root.mkdir()
bin_dir = ROOT / "bin"
bin_dir.mkdir()
fake = bin_dir / "pkgconf-mock"
fake.write_text(f'''#!{PYTHON}
import json, os, sys
with open(os.environ["E12_MOCK_LOG"], "a") as f:
 f.write(json.dumps({{"argv":sys.argv[1:],"libdir":os.environ.get("PKG_CONFIG_LIBDIR")}})+"\\n")
if "--variable=prefix" in sys.argv: print("/usr/pkg")
elif "--cflags" in sys.argv and "--libs" in sys.argv:
 print("-I/usr/pkg/include -DGN_X64_MOCK=1 -L/usr/pkg/lib -lfixture")
else: raise SystemExit("unexpected pkgconf call: "+repr(sys.argv[1:]))
''')
fake.chmod(0o755)
(bin_dir / "pkg-config").symlink_to(fake)
env = process.sanitized_environment()
env["PATH"] = str(bin_dir) + os.pathsep + os.defpath
env["PYTHONDONTWRITEBYTECODE"] = "1"
for key in ("PKG_CONFIG_LIBDIR", "PKG_CONFIG_PATH", "PKG_CONFIG_SYSROOT_DIR",
            "PYTHONPATH", "PYTHONHOME"):
    env.pop(key, None)

buildconfig = '''declare_args() {
  fixture_host_os = "mac"
  fixture_target_os = "netbsd"
  fixture_cpu = "arm64"
  fixture_target_sysroot = true
  fixture_custom = false
}
host_os = fixture_host_os
host_cpu = "arm64"
current_os = fixture_target_os
current_cpu = fixture_cpu
target_os = fixture_target_os
target_cpu = fixture_cpu
host_toolchain = "//toolchain:host"
set_default_toolchain("//toolchain:default")
is_android = false
is_linux = current_os == "linux"
is_chromeos = false
is_mac = current_os == "mac"
is_ios = false
is_fuchsia = false
'''
build = '''import("//build/config/linux/pkg_config.gni")
write_file("$root_build_dir/arguments.json", {
  common = common_pkg_config_args
  target = pkg_config_args
  host = host_pkg_config_args
}, "json")
pkg_config("metadata") { packages = [ "fixture" ] }
group("all") { public_configs = [ ":metadata" ] }
'''
toolchains = '''toolchain("default") {
  tool("stamp") { command = "touch {{output}}" }
}
toolchain("host") {
  tool("stamp") { command = "touch {{output}}" }
  toolchain_args = {
    current_os = host_os
    current_cpu = host_cpu
  }
}
'''
commands = []
def run(name, cmd, cwd, run_env):
    try:
        result = capture(list(map(str, cmd)), cwd=cwd, env=run_env)
    except CommandError as error:
        result = error
    (LOGS / (name + ".out")).write_bytes(result.stdout)
    (LOGS / (name + ".err")).write_bytes(result.stderr)
    commands.append({"name": name, "argv": list(map(str, cmd)), "status": result.returncode})
    write_json(ROOT / "commands.json", commands, exclusive=False)
    return result

cases = {
 "cross-x64": dict(fixture_cpu="x64"),
 "cross-x64-custom": dict(fixture_cpu="x64", fixture_custom=True),
 "cross-arm64": dict(fixture_cpu="arm64"),
 "cross-arm64-custom": dict(fixture_cpu="arm64", fixture_custom=True),
 "native-x64": dict(fixture_host_os="netbsd", fixture_cpu="x64"),
 "native-arm64": dict(fixture_host_os="netbsd", fixture_cpu="arm64"),
 "linux-x64": dict(fixture_target_os="linux", fixture_cpu="x64"),
 "x64-no-sysroot": dict(fixture_cpu="x64", fixture_target_sysroot=False),
}
observations = {}
for version in ("before", "after"):
    tree = ROOT / version
    for rel in FILES:
        dest = tree / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / rel, dest)
    # The template imports this file only to determine whether Chromium's
    # cached-result mechanism is active. Keep the small fixture uncached.
    (tree / "build/config/gclient_args.gni").write_text("# no Chromium cache args in this isolated fixture\n")
    (tree / PKG).write_text(pkg_text)
    (tree / RUST).write_text(rust_text)
    if version == "after":
        applied = run("patch", ["patch", "-p1", "-F0", "-i", PATCH], tree, env)
        assert applied.returncode == 0, (applied.stdout, applied.stderr)
        assert pkg_after in (tree / PKG).read_text()
        assert rust_after in (tree / RUST).read_text()
    (tree / ".gn").write_text('buildconfig = "//BUILDCONFIG.gn"\nscript_executable = ' +
                              json.dumps(str(PYTHON)) + "\n")
    (tree / "BUILDCONFIG.gn").write_text(buildconfig)
    (tree / "BUILD.gn").write_text(build)
    (tree / "toolchain").mkdir()
    (tree / "toolchain/BUILD.gn").write_text(toolchains)
    for name, values in cases.items():
        out = tree / "out" / name
        out.mkdir(parents=True)
        args_gn = dict(fixture_host_os="mac", fixture_target_os="netbsd",
                       fixture_cpu="arm64", fixture_target_sysroot=True, fixture_custom=False)
        args_gn.update(values)
        selected_sysroot = str(mock_root) if args_gn["fixture_target_sysroot"] else ""
        args_gn.update(sysroot=selected_sysroot, target_sysroot=selected_sysroot,
                       emberbsd_target_sysroot=selected_sysroot,
                       pkg_config=str(fake) if args_gn["fixture_custom"] else "")
        (out / "args.gn").write_text("\n".join(
            f"{k} = {json.dumps(v)}" for k, v in args_gn.items()) + "\n")
        mock_log = LOGS / f"{version}-{name}.mock.jsonl"
        run_env = dict(env, E12_MOCK_LOG=str(mock_log))
        gen = run(f"{version}-{name}-gen", [GN, "gen", out, "--root=" + str(tree)], tree, run_env)
        assert gen.returncode == 0, (version, name, gen.stdout[-3000:], gen.stderr[-3000:])
        config = {}
        for field in ("libs", "lib_dirs", "cflags_c"):
            desc = run(f"{version}-{name}-desc-{field}",
                       [GN, "desc", out, "//:metadata", field, "--format=json",
                        "--root=" + str(tree)], tree, run_env)
            assert desc.returncode == 0, (version, name, field, desc.stdout, desc.stderr)
            value = json.loads(desc.stdout).get("//:metadata", {}).get(field, [])
            config[field] = value
        gn_args = json.loads((out / "arguments.json").read_text())
        calls = [json.loads(line) for line in mock_log.read_text().splitlines()] if mock_log.exists() else []
        observations[f"{version}-{name}"] = {"config": config, "args": gn_args, "out": str(out),
                                               "mock_calls": calls, "gn": gen.returncode}

# Verify actual empty-vs-nonempty metadata, not just selector text.
for name in ("cross-x64", "cross-x64-custom"):
    old = observations["before-" + name]
    new = observations["after-" + name]
    assert old["config"]["libs"] == [] and old["mock_calls"] == []
    assert new["config"]["libs"] == ["fixture"]
    assert len(new["config"]["lib_dirs"]) == 1
    assert "mock-sysroot/usr/pkg/lib" in new["config"]["lib_dirs"][0]
    include = new["config"]["cflags_c"][0].removeprefix("-isystem")
    assert "mock-sysroot/usr/pkg/include" in include
    # GN evaluates the config once during gen and once per queried property.
    assert len(new["mock_calls"]) == 8
    common = new["args"]["common"]
    assert "--allow-cross-sysroot" in common
    idx = common.index("--system_libdir")
    assert common[idx + 1] == "pkg/lib"
for name in ("cross-arm64", "cross-arm64-custom"):
    old, new = observations["before-" + name], observations["after-" + name]
    old_calls = [(c["argv"], c["libdir"].split(":")[:3]) for c in old["mock_calls"]]
    new_calls = [(c["argv"], c["libdir"].split(":")[:3]) for c in new["mock_calls"]]
    assert old["config"] == new["config"] and old["args"] == new["args"]
    assert old_calls == new_calls
    assert old["config"]["libs"] == ["fixture"]
for name in ("native-x64", "native-arm64", "linux-x64", "x64-no-sysroot"):
    old, new = observations["before-" + name], observations["after-" + name]
    assert all(old[key] == new[key] for key in ("config", "args", "mock_calls"))
    assert old["config"]["libs"] == [] and old["mock_calls"] == []
for rel, digest in hashes.items():
    assert sha256_file(SOURCE / rel) == digest
for rel in (PKG, RUST):
    check = run("format-" + rel.name, [GN, "format", "--dry-run", ROOT / "after" / rel], ROOT, env)
    assert check.returncode == 0, (rel, check.stdout, check.stderr)
result = {
 "status": "PASS", "source_head": head, "source_sha256": hashes,
 "patch_sha256": sha256_file(PATCH), "gn": str(GN),
 "test_sha256": sha256_file(Path(__file__).resolve(strict=True)),
 "gn_version": run("gn-version", [GN, "--version"], ROOT, env).stdout.decode().strip(),
 "sdk_source": str(SDK), "sdk_api": 1,
 "sdk_sha256": {str(m.__file__): sha256_file(m.__file__) for m in
                (emberbsd_sdk, errors, inventory, jsonio, process)},
 "metadata_snapshots": len(observations), "cases": observations,
 "mock_sysroot": str(mock_root), "mock_pc_files": 0, "commands": commands,
 "scope": "8 GN configurations before and after; exact production pkg_config.gni and pkg-config.py; mock pkgconf and empty synthetic sysroot. Native Linux/NetBSD are controlled GN inputs on macOS, not native-host execution. No shared sysroot, real pkgconf, target compilation, linking, or Electron build."
}
write_json(ROOT / "result.json", result)
print(json.dumps({"status": "PASS", "metadata_snapshots": len(observations),
 "x64": "baseline GN succeeds with empty metadata; patched GN consumes synthetic pkgconf flags",
 "arm64": "baseline behavior preserved", "result": str(ROOT / "result.json")}, sort_keys=True))
