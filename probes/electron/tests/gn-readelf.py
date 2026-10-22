#!/usr/bin/env python3.15
"""Check carried unbundle patches with production GN solink and assembler rules."""
# Origin: EmberBSD (AI-assisted). Only the unrelated host rustc version probe executes; no compilation runs.
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
for name in ("source", "gn", "readelf", "rustc", "sdk-source"):
    parser.add_argument("--" + name, required=True, type=Path)
parser.add_argument("new_work", type=Path, metavar="NEW_WORK")
args = parser.parse_args()
if not args.sdk_source.is_absolute():
    parser.error('--sdk-source must be absolute')
SDK_SOURCE = args.sdk_source.resolve(strict=True)
package = SDK_SOURCE / 'src/emberbsd_sdk'
if not (package / '__init__.py').is_file():
    parser.error('the selected SDK source has no emberbsd_sdk API')
sys.path.insert(0, str(SDK_SOURCE / 'src'))
import emberbsd_sdk
if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error('the selected SDK must provide API version 1')
if Path(emberbsd_sdk.__file__).resolve().parent != package.resolve():
    parser.error('SDK package must come from the selected source')
from emberbsd_sdk import errors, inventory, jsonio, process
SDK_MODULES = (emberbsd_sdk, errors, inventory, jsonio, process)
if any(not Path(module.__file__).resolve().is_relative_to(package.resolve()) for module in SDK_MODULES):
    parser.error('SDK modules must come from the selected source')
CommandError = errors.CommandError
capture = process.capture
sha256_file = inventory.sha256_file
write_json = jsonio.write_json
source, gn, readelf, rustc = (p.resolve(strict=True) for p in (args.source, args.gn, args.readelf, args.rustc))
if not args.new_work.is_absolute():
    parser.error("NEW_WORK must be absolute")
root = args.new_work.resolve()
if root.is_relative_to(source):
    parser.error("NEW_WORK must be outside the source")
root.mkdir(parents=True)
logs = root / "logs"
logs.mkdir()
patch = Path(__file__).resolve().parent.parent / "patches/gn-unbundle-readelf.patch"
shutil.copy2(patch, root / patch.name)
asm_patch = patch.with_name("gn-unbundle-asmflags.patch")
shutil.copy2(asm_patch, root / asm_patch.name)
member = Path("build/toolchain/linux/unbundle/BUILD.gn")
provided = (source / member).read_text()
addition = '''  # Do not use a host PATH executable to inspect cross-built NetBSD ELF files.
  if (current_os == "netbsd" && host_os != "netbsd") {
    readelf = getenv("READELF")
    assert(readelf != "",
           "cross-building for NetBSD requires READELF for the target toolchain")
  }
'''
assert provided.count(addition) in (0, 1), "unrecognized readelf guard"
original = provided.replace(addition, "")
for line in ('  extra_asmflags = getenv("ASFLAGS")\n', '  extra_asmflags = getenv("BUILD_ASFLAGS")\n'):
    assert original.count(line) in (0, 1), "unrecognized assembler flag owner"
    original = original.replace(line, "")
assert original.count('  nm = getenv("NM")\n') == 1
assert original.count('  nm = getenv("BUILD_NM")\n') == 1
commands = []


def run(name, argv, cwd, env):
    try:
        result = capture(list(map(str, argv)), cwd=cwd, env=env)
    except CommandError as error:
        result = error
    (logs / (name + ".stdout")).write_bytes(result.stdout)
    (logs / (name + ".stderr")).write_bytes(result.stderr)
    commands.append(dict(name=name, argv=list(map(str, argv)), cwd=str(cwd), status=result.returncode))
    write_json(root / "commands.json", commands, exclusive=False)
    return result


# Link production inputs. Copy only the one modified leaf and fixture root.
# PYTHONDONTWRITEBYTECODE keeps imported production scripts read-only.
def overlay(destination, relative=Path()):
    destination.mkdir()
    for entry in (source / relative).iterdir():
        if entry.name.startswith(".") or entry.name == "out" or entry.name.endswith(".orig"):
            continue
        child = relative / entry.name
        if child in (Path("BUILD.gn"), member):
            continue
        if child in member.parents and child != Path("."):
            overlay(destination / entry.name, child)
        else:
            (destination / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())


config = '''declare_args() {
  host_toolchain = "//build/toolchain/linux/unbundle:host"
  fixture_host_os = ""
  fixture_current_os = ""
}
if (fixture_host_os != "") { host_os = fixture_host_os }
if (fixture_current_os != "") { current_os = fixture_current_os }
if (current_os == "") { current_os = target_os }
if (current_cpu == "") { current_cpu = target_cpu }
is_clang = false
is_debug = false
is_component_build = false
is_official_build = false
enable_strict_deps = false
set_default_toolchain("//build/toolchain/linux/unbundle:default")
is_android = current_os == "android"
is_chromeos = current_os == "chromeos"
is_fuchsia = current_os == "fuchsia"
is_ios = current_os == "ios"
is_linux = current_os == "linux" || current_os == "netbsd"
is_bsd = current_os == "netbsd"
is_mac = current_os == "mac"
is_apple = is_mac || is_ios
is_wasm = false
is_watchos = false
is_win = false
is_posix = true
is_netbsd = current_os == "netbsd"
TESTONLY_AND_VISIBILITY = [ "testonly", "visibility" ]
'''
build = '''shared_library("probe") { sources = [ "probe.cc", "probe_asm.S" ] }
group("all") {
  deps = [ ":probe", ":probe(//build/toolchain/linux/unbundle:host)" ]
}
'''
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
for key in ("CC", "CXX", "AR", "NM", "BUILD_CC", "BUILD_CXX", "BUILD_AR", "BUILD_NM"):
    environment[key] = "fixture-" + key.lower()
for key in ("READELF", "CFLAGS", "CPPFLAGS", "CXXFLAGS", "LDFLAGS", "BUILD_CFLAGS",
            "BUILD_CPPFLAGS", "BUILD_CXXFLAGS", "BUILD_LDFLAGS", "ASFLAGS", "BUILD_ASFLAGS",
            "PYTHONPATH", "PYTHONHOME"):
    environment.pop(key, None)
cases = {
    "cross-missing": {},
    "cross-selected": {},
    "native-netbsd": {"fixture_host_os": "netbsd"},
    "linux": {"target_os": "linux"},
    "secondary-linux": {"fixture_current_os": "linux"},
}
observations = {}
for version in ("before", "after"):
    tree = root / version
    overlay(tree)
    (tree / member).write_text(original)
    (tree / ".gn").write_text('buildconfig = "//fixture_config.gn"\nscript_executable = '
                              + json.dumps(sys.executable) + "\n")
    (tree / "fixture_config.gn").write_text(config)
    (tree / "BUILD.gn").write_text(build)
    (tree / "probe.cc").write_text("int fixture_probe() { return 0; }\n")
    (tree / "probe_asm.S").write_text(".text\n")
    if version == "after":
        result = run("apply-carried-patch", ["patch", "-p1", "-F", "0", "-i", patch], tree, environment)
        assert result.returncode == 0, result.stdout + result.stderr
        result = run("apply-assembler-patch", ["patch", "-p0", "-F", "0", "-i", asm_patch], tree, environment)
        assert result.returncode == 0, result.stdout + result.stderr
    assert (tree / "build/toolchain/gcc_toolchain.gni").resolve() == (source / "build/toolchain/gcc_toolchain.gni").resolve()
    for name, extra in cases.items():
        output = tree / "out" / name
        output.mkdir(parents=True)
        # Some source revisions probe ./rustc -V during GN evaluation.
        (output / "rustc").symlink_to(rustc)
        values = dict(target_os="netbsd", target_cpu="arm64", use_sysroot=False)
        values.update(extra)
        (output / "args.gn").write_text("\n".join(k + " = " + json.dumps(v) for k, v in values.items()) + "\n")
        env = dict(environment)
        if name == "cross-selected":
            env["READELF"] = str(readelf)
            env["ASFLAGS"] = "-DPORTS_TARGET_ASM=1"
            env["BUILD_ASFLAGS"] = "-DPORTS_HOST_ASM=1"
        result = run(version + "-" + name, [gn, "gen", output, "--root=" + str(tree)], root, env)
        refused = version == "after" and name == "cross-missing"
        if refused:
            assert result.returncode != 0 and b"cross-building for NetBSD requires READELF" in result.stdout + result.stderr
            observations[version + "-" + name] = dict(status=result.returncode)
            continue
        assert result.returncode == 0, result.stdout + result.stderr
        target = (output / "toolchain.ninja").read_text()
        host = (output / "host/toolchain.ninja").read_text()
        selected = str(readelf) if version == "after" and name == "cross-selected" else "readelf"
        assert '--readelf="' + selected + '"' in target
        assert '--readelf="readelf"' in host
        assert '--strip=' not in target and '--strip=' not in host
        assert ": solink " in (output / "obj/probe.ninja").read_text()
        assert ": host_solink " in (output / "host/obj/probe.ninja").read_text()
        assert ": asm " in (output / "obj/probe.ninja").read_text()
        assert ": host_asm " in (output / "host/obj/probe.ninja").read_text()
        target_asm = target.split("rule asm\n", 1)[1].splitlines()[0]
        host_asm = host.split("rule host_asm\n", 1)[1].splitlines()[0]
        if version == "after" and name == "cross-selected":
            assert "-DPORTS_TARGET_ASM=1" in target_asm and "PORTS_HOST_ASM" not in target_asm
            assert "-DPORTS_HOST_ASM=1" in host_asm and "PORTS_TARGET_ASM" not in host_asm
        else:
            assert "PORTS_TARGET_ASM" not in target_asm and "PORTS_HOST_ASM" not in target_asm
            assert "PORTS_TARGET_ASM" not in host_asm and "PORTS_HOST_ASM" not in host_asm
        for rule, text in (("cxx", target), ("host_cxx", host)):
            cxx = text.split("rule " + rule + "\n", 1)[1].splitlines()[0]
            assert "PORTS_TARGET_ASM" not in cxx and "PORTS_HOST_ASM" not in cxx
        assert "build/toolchain/gcc_toolchain.gni" in (output / "build.ninja.d").read_text()
        observations[version + "-" + name] = dict(status=0, target_readelf=selected, host_readelf="readelf",
            target_asm=target_asm, host_asm=host_asm)
for name in ("native-netbsd", "linux", "secondary-linux"):
    for key in ("target_asm", "host_asm"):
        assert observations["before-" + name][key] == observations["after-" + name][key]
assert (source / member).read_text() == provided
inputs = {str(p): sha256_file(p) for p in
          (source / member, source / "build/toolchain/gcc_toolchain.gni",
           source / "build/toolchain/gcc_solink_wrapper.py", gn, readelf, rustc, patch, asm_patch)}
write_json(root / "result.json", dict(status="PASS", cases=observations,
    input_sha256=inputs, sdk_source=str(SDK_SOURCE), sdk_api=1,
    sdk_sha256={str(m.__file__): sha256_file(m.__file__) for m in SDK_MODULES},
    scope="Production GN rules and generated solink only. Only host rustc -V ran; no compilation, linking or target execution."))
print(json.dumps(dict(status="PASS", GN_cases=len(observations), result=str(root / "result.json"))))
