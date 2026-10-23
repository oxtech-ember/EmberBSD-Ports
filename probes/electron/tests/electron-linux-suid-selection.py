#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted source-level regression for Electron).
"""Check pinned Linux SUID-helper GN selections with host GN only."""

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

parser = argparse.ArgumentParser(description=__doc__)
for name in ("sdk-source", "chromium-source", "patch", "gn", "work-dir"):
    parser.add_argument("--" + name, required=True, type=Path)
options = parser.parse_args()
if not options.work_dir.is_absolute():
    parser.error("--work-dir must be an absolute path")
SDK, SOURCE, PATCH, GN = (path.resolve(strict=True) for path in
                         (options.sdk_source, options.chromium_source,
                          options.patch, options.gn))
WORK = options.work_dir.resolve()
for root in (SOURCE, SDK):
    if WORK.is_relative_to(root) or root.is_relative_to(WORK):
        parser.error("--work-dir must be separate from the sources and SDK")
if WORK.exists():
    parser.error("--work-dir must name a new, unused directory")
SDK_PACKAGE = SDK / "src/emberbsd_sdk"
if not (SDK_PACKAGE / "__init__.py").is_file():
    parser.error("the selected SDK source has no emberbsd_sdk API")
sys.path.insert(0, str(SDK / "src"))
import emberbsd_sdk
from emberbsd_sdk import errors, inventory, jsonio, process

SDK_MODULES = (emberbsd_sdk, errors, inventory, jsonio, process)
if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error("the selected SDK must provide integer API version 1")
if any(not Path(module.__file__).resolve().is_relative_to(SDK_PACKAGE.resolve())
       for module in SDK_MODULES):
    parser.error("all SDK modules must come from the selected SDK source")
if Path(emberbsd_sdk.__file__).resolve().parent != SDK_PACKAGE.resolve():
    parser.error("emberbsd_sdk must come from the selected SDK source")

PINNED_BASE = {
    "electron/BUILD.gn":
        "02f65f6a70687f659e7445160ecfdf0ea9d33e207e6ac913a9cd857e663fc4e6",
    "sandbox/linux/BUILD.gn":
        "c04c3323768e561475bac677a3c4d6d8d9d07a29f18c3328e182a5a34899a559",
}
CONTEXT = ("build/config/BUILDCONFIG.gn", "sandbox/policy/BUILD.gn")
OS_NAMES = ("linux", "chromeos", "netbsd", "freebsd", "openbsd", "mac",
            "win", "winuwp", "android", "fuchsia", "ios", "watchos",
            "emscripten")
BSD_NAMES = ("netbsd", "freebsd", "openbsd")
HELPER = "//sandbox/linux:chrome_sandbox"
BASE_DATA = [":electron_app", ":electron_version_file", ":licenses"]
STRIPPED_DATA = [":strip_chrome_crashpad_handler", ":strip_chrome_sandbox",
                 ":strip_electron_binary", ":strip_libffmpeg_shlib",
                 ":strip_libvk_swiftshader_shlib"]
GENERIC_STRIPS = {
    "strip_electron_binary": [":electron_app"],
    "strip_chrome_crashpad_handler":
        ["//components/crash/core/app:chrome_crashpad_handler"],
    "strip_electron_xcache_binary": [":electron_xcache"],
    "strip_libffmpeg_shlib": ["//third_party/ffmpeg"],
    "strip_libvk_swiftshader_shlib":
        ["//third_party/swiftshader/src/Vulkan:swiftshader_libvulkan"],
}
PATCH_TOOL = shutil.which("patch")
if PATCH_TOOL is None:
    parser.error("the host patch utility is required")
PATCH_TOOL = Path(PATCH_TOOL).resolve(strict=True)
ENV = {"PATH": str(GN.parent) + os.pathsep + "/usr/bin:/bin", "LC_ALL": "C",
       "PYTHONDONTWRITEBYTECODE": "1"}
report = {"status": "RUNNING", "runs": [], "selections": {},
          "expected_baseline_rejections": []}


def save():
    jsonio.write_json(WORK / "summary.json", report, exclusive=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bounded(text, first, last):
    # Locate a production fragment. Only GN evaluates its expressions.
    if text.count(first) != 1 or text.count(last) != 1:
        raise AssertionError("expected unique production fragment boundaries")
    start = text.index(first)
    return text[start:text.index(last, start)]


def command(argv, cwd):
    argv = list(map(str, argv))
    try:
        result = process.capture(argv, cwd=cwd, env=ENV)
        status, stdout, stderr = 0, result.stdout, result.stderr
    except errors.CommandError as error:
        status, stdout, stderr = error.returncode, error.stdout, error.stderr
    receipt = {"argv": argv, "cwd": str(cwd), "returncode": status,
               "stdout": stdout.decode("utf-8", "replace"),
               "stderr": stderr.decode("utf-8", "replace")}
    report["runs"].append(receipt)
    save()
    if status != 0:
        raise AssertionError(f"command failed ({status}): {argv!r}\n"
                             + receipt["stdout"] + receipt["stderr"])
    return receipt


def source_tree(name, contents):
    tree = WORK / name
    for relative, data in contents.items():
        path = tree / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return tree


def apply_patch(tree, reverse=False):
    argv = [PATCH_TOOL, "-f", "-p1", "-F", "0"]
    if reverse:
        argv.append("-R")
    return command([*argv, "-i", PATCH], tree)


def fragments(electron, sandbox, policy):
    app = bounded(electron, '    if (is_linux) {\n      ldflags = [',
                  '\n  }\n\n  if (is_official_build)')
    dist = bounded(electron, 'dist_zip("electron_dist_zip") {\n',
                   '\n}\n\ndist_zip("electron_ffmpeg_zip")').split('\n', 1)[1]
    strips = bounded(
        electron,
        'if (is_linux && is_official_build) {\n  strip_binary("strip_electron_binary")',
        '  strip_binary("strip_mksnapshot_binary")') + '}\n'
    comment = '  # The setuid sandbox for Linux.\n'
    if sandbox.count(comment) != 1:
        raise AssertionError("expected one Linux SUID-helper provider")
    index = sandbox.index(comment)
    provider_start = sandbox.rfind('\nif (', 0, index) + 1
    provider_end = sandbox.index('  executable("chrome_sandbox") {', index)
    provider = sandbox[provider_start:provider_end] + '  provider = true\n}\n'
    assignments = [line.strip() for line in sandbox.splitlines()
                   if line.strip().startswith('compile_suid_client = ')]
    if len(assignments) != 1:
        raise AssertionError("expected one production SUID-client assignment")
    netbsd_policy = bounded(policy, '  if (is_netbsd) {', '  if (is_freebsd) {')
    return {"app": app, "dist": dist, "strips": strips,
            "provider": provider, "client": assignments[0],
            "netbsd_policy": netbsd_policy}


def fixture_text(parts):
    # The adapter records strip declarations without running the strip action.
    prefix = '''template("strip_binary") {
  entry = {
    binary_input = invoker.binary_input
    symbol_output = invoker.symbol_output
    compressed = invoker.compress_debug_sections
    deps = invoker.deps
  }
  write_file("$root_build_dir/$target_name.json", entry, "json")
}
toolchain("default") {}
group("probe") {}
electron_project_name = "electron"
is_component_build = false
is_component_ffmpeg = true
electron_use_resource_allowlist = true
'''
    return (prefix + parts["client"] + '\nprovider = false\n'
            + parts["provider"]
            + 'app_selection = {\n  deps = []\n  configs = []\n  ldflags = []\n'
            + parts["app"] + '\n}\ndist_selection = {\n' + parts["dist"]
            + '\n}\npolicy_selection = {\n  sources = []\n  deps = []\n  libs = []\n'
            + parts["netbsd_policy"] + '\n}\n' + parts["strips"] + '''result = {
  app = app_selection
  dist = dist_selection
  policy = policy_selection
  provider = provider
  compile_suid_client = compile_suid_client
  fixture_context = [electron_project_name, is_component_build,
                     is_component_ffmpeg, electron_use_resource_allowlist]
}
write_file("$root_build_dir/selection.json", result, "json")
''')


class HelperSelectionError(AssertionError):
    pass


def require(actual, expected, name):
    if actual != expected:
        raise HelperSelectionError(f"{name}: expected {expected!r}, got {actual!r}")


def require_bsd_helper_absent(entry):
    require(entry["provider"], False, "BSD Linux helper provider")
    require(entry["app"]["deps"], [], "BSD app helper dependency")
    require(HELPER in entry["dist"]["data_deps"], False, "BSD dist helper")
    require(":strip_chrome_sandbox" in entry["dist"]["data_deps"], False,
            "BSD dist helper strip dependency")
    require(entry["helper_strip"], False, "BSD helper strip target")


def check_selection(entry, stage, os_name, official):
    bsd = os_name in BSD_NAMES
    elf_family = os_name in ("linux", *BSD_NAMES)
    helper_selected = elf_family and (stage == "before" or not bsd)
    data = BASE_DATA + (STRIPPED_DATA if elf_family and official else [])
    if elf_family:
        data = data + [HELPER]
    if stage == "after" and bsd:
        data = [name for name in data if name not in
                (HELPER, ":strip_chrome_sandbox")]
    require(entry["app"]["deps"], [HELPER] if helper_selected else [], "app deps")
    require(entry["app"]["configs"],
            ["//build/config/gcc:rpath_for_built_shared_libraries"]
            if elf_family else [], "app configs")
    require(entry["app"]["ldflags"],
            ["-pie", "-Wl,--whole-archive", "obj/third_party/electron_node/deps/uv/libuv.a",
             "-Wl,--no-whole-archive"] if elf_family else [], "app ELF flags")
    require(entry["dist"]["data_deps"], data, "dist data deps")
    require(entry["dist"]["deps"], data + [":electron_resource_allowlist_check"],
            "dist build-order deps")
    require(entry["provider"], os_name in ("linux", "chromeos")
            or stage == "before" and bsd, "helper provider")
    require(entry["compile_suid_client"], os_name in ("linux", "chromeos"),
            "existing SUID client selection")
    require(entry["helper_strip"], helper_selected and official, "helper strip")
    require(entry["generic_strips"],
            sorted(GENERIC_STRIPS) if elf_family and official else [],
            "generic ELF strip targets")
    expected_policy = {
        "sources": ["netbsd/sandbox_netbsd.cc", "netbsd/sandbox_netbsd.h"],
        "deps": ["//sandbox:sandbox_buildflags", "//ui/gfx/x"], "libs": ["util"],
    } if os_name == "netbsd" else {"sources": [], "deps": [], "libs": []}
    require(entry["policy"], expected_policy, "existing NetBSD policy selection")


def main():
    originals = {name: (SOURCE / name).read_bytes() for name in (*PINNED_BASE, *CONTEXT)}
    input_hashes = {name: digest(data) for name, data in originals.items()}
    # The exact two unified-diff paths are the only permitted patch outputs.
    headers = [line for line in PATCH.read_text().splitlines()
               if line.startswith(("--- ", "+++ "))]
    expected_headers = [item for name in PINNED_BASE
                        for item in ("--- a/" + name, "+++ b/" + name)]
    if headers != expected_headers:
        raise AssertionError("patch must contain only the two pinned GN file diffs")
    report.update({"python": sys.version.split()[0], "sdk_api_version": 1,
                   "sdk_module_origins": {module.__name__: str(Path(module.__file__).resolve())
                                          for module in SDK_MODULES},
                   "inputs_sha256": input_hashes, "patch_sha256": inventory.sha256_file(PATCH),
                   "pinned_baseline_sha256": PINNED_BASE, "gn_sha256": inventory.sha256_file(GN)})
    current = {name: originals[name] for name in PINNED_BASE}
    before_tree = source_tree("source-before", current)
    already_patched = any(input_hashes[name] != value for name, value in PINNED_BASE.items())
    if already_patched:
        apply_patch(before_tree, reverse=True)
    before = {name: (before_tree / name).read_bytes() for name in PINNED_BASE}
    if {name: digest(data) for name, data in before.items()} != PINNED_BASE:
        raise AssertionError("input or reversed patch did not recover the pinned baseline")
    after_tree = source_tree("source-after", before)
    apply_patch(after_tree)
    after = {name: (after_tree / name).read_bytes() for name in PINNED_BASE}
    if already_patched and after != current:
        raise AssertionError("forward patch did not reproduce the already-patched input")
    if after == before:
        raise AssertionError("patch did not change the GN selection")
    report["source_state"] = "already-patched" if already_patched else "baseline"
    report["patched_sha256"] = {name: digest(data) for name, data in after.items()}
    config = originals[CONTEXT[0]].decode("utf-8")
    last = 'is_posix = !is_win && !is_fuchsia\n'
    platforms = bounded(config, 'is_android = current_os == "android"\n', last) + last
    (WORK / "platform-assignments.gni").write_text(platforms)
    report["platform_assignments_sha256"] = digest(platforms.encode())
    report["gn_version"] = command([GN, "--version"], WORK)["stdout"].strip()
    for stage, contents in (("before", before), ("after", after)):
        parts = fragments(contents["electron/BUILD.gn"].decode(),
                          contents["sandbox/linux/BUILD.gn"].decode(),
                          originals[CONTEXT[1]].decode())
        root = WORK / "gn-fixture" / stage
        root.mkdir(parents=True, exist_ok=False)
        (root / ".gn").write_text('buildconfig = "//BUILDCONFIG.gn"\n')
        (root / "BUILDCONFIG.gn").write_text('''declare_args() {
  test_os = "linux"
  is_official_build = false
}
current_os = test_os
''' + platforms + 'set_default_toolchain("//:default")\n')
        (root / "BUILD.gn").write_text(fixture_text(parts))
        report.setdefault("fixture_sha256", {})[stage] = {
            path.name: inventory.sha256_file(path) for path in root.iterdir()}
        report["selections"][stage] = {}
        for os_name in OS_NAMES:
            for official in (False, True):
                key = os_name + "-" + str(official).lower()
                out = root / ("out-" + key)
                # A GN failure is always fatal, never an expected rejection.
                command([GN, "gen", out, "--root=" + str(root),
                         "--args=test_os=" + json.dumps(os_name)
                         + " is_official_build=" + str(official).lower()], root)
                entry = json.loads((out / "selection.json").read_text())
                entry["helper_strip"] = (out / "strip_chrome_sandbox.json").exists()
                entry["generic_strips"] = sorted(
                    name for name in GENERIC_STRIPS if (out / (name + ".json")).exists())
                strip_records = {name: json.loads((out / (name + ".json")).read_text())
                                 for name in entry["generic_strips"]}
                for name, record in strip_records.items():
                    require(record["deps"], GENERIC_STRIPS[name], name + " deps")
                    require(record["compressed"], True, name + " compressed debug sections")
                check_selection(entry, stage, os_name, official)
                if os_name in BSD_NAMES:
                    if stage == "before":
                        try:
                            require_bsd_helper_absent(entry)
                        except HelperSelectionError as error:
                            report["expected_baseline_rejections"].append(
                                {"case": key, "reason": str(error), "gn_returncode": 0})
                        else:
                            raise AssertionError("faulty baseline passed the BSD helper contract")
                    else:
                        require_bsd_helper_absent(entry)
                if stage == "after" and os_name not in BSD_NAMES:
                    baseline = report["selections"]["before"][key]
                    for member in ("app", "policy", "provider", "compile_suid_client",
                                   "helper_strip", "generic_strips"):
                        require(entry[member], baseline[member], "unchanged non-BSD " + member)
                    require(entry["dist"]["data_deps"], baseline["dist"]["data_deps"],
                            "unchanged non-BSD dist")
                if stage == "after":
                    require(strip_records, report["strip_records"]["before"][key],
                            "unchanged generic ELF strip inputs and outputs")
                report["selections"][stage][key] = entry
                report.setdefault("strip_records", {}).setdefault(stage, {})[key] = strip_records
                report.setdefault("output_json_sha256", {}).setdefault(stage, {})[key] = {
                    path.name: inventory.sha256_file(path) for path in out.glob("*.json")}
                # The JSON receipts retain the observations; generated GN outputs are temporary.
                shutil.rmtree(out)
                save()
    for name, expected in input_hashes.items():
        if inventory.sha256_file(SOURCE / name) != expected:
            raise AssertionError("source changed during this check: " + name)
    count = sum(len(cases) for cases in report["selections"].values())
    require(count, 52, "successful GN observations")
    require(len(report["expected_baseline_rejections"]), 6, "causal BSD rejections")
    report.update({"status": "PASS", "gn_invocations": count, "source_inputs_unchanged": True,
                   "scope": "Bounded production GN expressions only. No build actions run. "
                            "NetBSD OS isolation and installed sandbox behavior are not tested."})
    save()
    print(json.dumps({"status": report["status"], "gn_invocations": count,
                      "source_state": report["source_state"], "summary": str(WORK / "summary.json")}))


WORK.mkdir(parents=True, exist_ok=False)
try:
    main()
except Exception as error:
    report.update({"status": "FAIL", "error": str(error)})
    save()
    raise
