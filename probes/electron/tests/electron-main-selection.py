#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted source-level regression for E12 Electron).
"""Check the pinned Electron app source selector with host GN only."""

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

parser = argparse.ArgumentParser(description=__doc__)
for name in ("sdk-source", "ports-root", "chromium-source", "electron-source",
             "patch", "gn"):
    parser.add_argument("--" + name, required=True, type=Path)
parser.add_argument("--work-dir", required=True, type=Path)
options = parser.parse_args()

if not options.work_dir.is_absolute():
    parser.error("--work-dir must be an absolute path")
SDK_SOURCE, PORTS, CHROMIUM, ELECTRON, PATCH, GN = (
    path.resolve(strict=True) for path in
    (options.sdk_source, options.ports_root, options.chromium_source,
     options.electron_source, options.patch, options.gn)
)
WORK = options.work_dir.resolve()
SOURCE_BUILD = ELECTRON / "BUILD.gn"
SOURCE_CONFIG = CHROMIUM / "build/config/BUILDCONFIG.gn"
if not SOURCE_BUILD.is_file():
    parser.error("--electron-source must contain BUILD.gn")
if not SOURCE_CONFIG.is_file():
    parser.error("--chromium-source must contain build/config/BUILDCONFIG.gn")
for root_name, root in (("Electron source", ELECTRON),
                        ("Chromium source", CHROMIUM),
                        ("Ports root", PORTS), ("SDK source", SDK_SOURCE)):
    if WORK.is_relative_to(root) or root.is_relative_to(WORK):
        parser.error("--work-dir must be separate from " + root_name)
if WORK.exists():
    parser.error("--work-dir must name a new, unused directory")

SDK_PACKAGE = SDK_SOURCE / "src/emberbsd_sdk"
if not (SDK_PACKAGE / "__init__.py").is_file():
    parser.error("the selected SDK source has no emberbsd_sdk API")
sys.path.insert(0, str(SDK_SOURCE / "src"))
import emberbsd_sdk

if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error("the selected SDK must provide integer API version 1")
if Path(emberbsd_sdk.__file__).resolve().parent != SDK_PACKAGE.resolve():
    parser.error("emberbsd_sdk must come from the selected SDK source")
from emberbsd_sdk import errors, inventory, jsonio, process

SDK_MODULES = (emberbsd_sdk, errors, inventory, jsonio, process)
if any(not Path(module.__file__).resolve().is_relative_to(SDK_PACKAGE.resolve())
       for module in SDK_MODULES):
    parser.error("all imported SDK modules must come from the selected SDK source")
capture = process.capture
CommandError = errors.CommandError
sha256_file = inventory.sha256_file
write_json = jsonio.write_json

PINNED_BASE_BUILD_SHA256 = (
    "908c98174081f6f916c9aa69dbdae2d14b746a1d86d3bff62b8e148ad5bdb7f8"
)
EXPECTED_LINUX = [
    "shell/app/electron_main_linux.cc",
    "shell/app/environ_linux.cc",
    "shell/app/uv_stdio_fix.cc",
    "shell/app/uv_stdio_fix.h",
]
EXPECTED_WIN = ["shell/app/electron_main_win.cc"]
EXPECTED_NETBSD = [
    "shell/app/electron_main_linux.cc",
    "shell/app/uv_stdio_fix.cc",
    "shell/app/uv_stdio_fix.h",
]
OS_NAMES = ("linux", "chromeos", "netbsd", "freebsd", "openbsd", "mac",
            "win", "winuwp", "android", "fuchsia", "ios", "watchos",
            "emscripten")

PATCH_TOOL = shutil.which("patch")
if PATCH_TOOL is None:
    parser.error("the host patch utility is required")
PATCH_TOOL = Path(PATCH_TOOL).resolve(strict=True)
ENV = {"PATH": str(GN.parent) + os.pathsep + "/usr/bin:/bin",
       "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}


def selector(text):
    marker = '  executable("electron_app") {'
    if text.count(marker) != 1:
        raise AssertionError("expected one generic electron_app executable")
    target = text.index(marker)
    start = text.index("    if (is_win) {", target)
    end = text.index('    include_dirs = [ "." ]', start)
    return text[start:end].rstrip()


def mac_sources(text):
    marker = '  mac_app_bundle("electron_app") {'
    if text.count(marker) != 1:
        raise AssertionError("expected one macOS electron_app bundle")
    start = text.index("    sources = [", text.index(marker))
    end = text.index("    ]", start)
    return re.findall(r'^\s*"([^"\n]+)"\s*,?$', text[start:end], re.MULTILINE)


def platform_assignments(text):
    # Copy this bounded production block. Only GN evaluates its expressions.
    first = 'is_android = current_os == "android"\n'
    last = 'is_posix = !is_win && !is_fuchsia\n'
    if text.count(first) != 1 or text.count(last) != 1:
        raise AssertionError("cannot locate the production OS definitions")
    start = text.index(first)
    end = text.index(last, start) + len(last)
    return text[start:end]


def late_netbsd_selector(before_selector, after_selector):
    # Reproduce the former faulty placement without evaluating the selector.
    branch = re.findall(
        r'    } else if \(current_os == "netbsd"\) {\n'
        r'      sources = \[\n(?:        "[^"\n]+",\n)+      \]\n',
        after_selector + "\n")
    closing = "\n    }"
    if len(branch) != 1 or not before_selector.endswith(closing):
        raise AssertionError("cannot construct the former late NetBSD branch")
    return before_selector[:-len(closing)] + "\n" + branch[0].rstrip() + closing


def fixture_build(selector_text, mac_list):
    selector_lines = "\n".join(
        "    " + line if line else "" for line in selector_text.splitlines())
    mac_values = ",\n".join(f'      "{name}"' for name in mac_list)
    return f'''toolchain("default") {{}}
if (is_mac) {{
  group("electron_app") {{
    sources = [
{mac_values}
    ]
    write_file("$root_build_dir/sources.json", sources, "json")
  }}
}} else {{
  group("electron_app") {{
    sources = []
{selector_lines}
    write_file("$root_build_dir/sources.json", sources, "json")
  }}
}}
'''


def command(argv, cwd, *, expected=0):
    try:
        result = capture(list(map(str, argv)), cwd=cwd, env=ENV)
        status, stdout, stderr = 0, result.stdout, result.stderr
    except CommandError as error:
        status, stdout, stderr = error.returncode, error.stdout, error.stderr
    if expected is not None and (status == 0) != (expected == 0):
        raise AssertionError(
            f"command status mismatch ({status}): {argv!r}\n"
            + stderr.decode("utf-8", "replace"))
    return {"argv": list(map(str, argv)), "cwd": str(cwd), "returncode": status,
            "stdout": stdout.decode("utf-8", "replace"),
            "stderr": stderr.decode("utf-8", "replace")}


def apply_patch(tree, reverse=False):
    argv = [str(PATCH_TOOL), "-f", "-p1", "-F", "0"]
    if reverse:
        argv.append("-R")
    argv.extend(["-i", str(PATCH)])
    return command(argv, tree)


def make_tree(name, build_bytes):
    tree = WORK / name
    target = tree / "electron/BUILD.gn"
    target.parent.mkdir(parents=True, exist_ok=False)
    target.write_bytes(build_bytes)
    return tree, target


def run_gn(root, stage, os_name):
    out = root / ("out-" + stage + "-" + os_name)
    argv = [str(GN), "gen", str(out), "--root=" + str(root),
            "--args=test_os=" + json.dumps(os_name)]
    result = command(argv, root, expected=None)
    result["stage"] = stage
    result["os"] = os_name
    receipt = root / (stage + "-" + os_name + ".json")
    write_json(receipt, result)
    if result["returncode"] != 0:
        raise AssertionError("GN must succeed before checking sources: "
                             + str(receipt))
    actual_file = out / "sources.json"
    actual = json.loads(actual_file.read_text())
    if (not isinstance(actual, list)
            or any(type(item) is not str for item in actual)):
        raise AssertionError("GN did not emit a source list")
    result["actual_sources"] = actual
    result["sources_json_sha256"] = sha256_file(actual_file)
    write_json(receipt, result, exclusive=False)
    return result


class SourceSelectionError(AssertionError):
    pass


def require_sources(actual, expected):
    if actual != expected:
        raise SourceSelectionError(f"expected {expected!r}, got {actual!r}")


def reject_netbsd_sources(actual):
    # Catch only a source-list mismatch. A GN error never reaches this check.
    try:
        require_sources(actual, EXPECTED_NETBSD)
    except SourceSelectionError as error:
        return {"status": "expected-rejection", "reason": str(error)}
    raise AssertionError("the faulty selector passed the NetBSD POSIX requirement")


def main():
    source_hash_before = sha256_file(SOURCE_BUILD)
    config_hash_before = sha256_file(SOURCE_CONFIG)
    platforms = platform_assignments(SOURCE_CONFIG.read_text())
    (WORK / "platform-assignments.gni").write_text(platforms)
    # An already-patched source is accepted only when reversing this exact
    # patch recovers the pinned baseline file byte for byte.
    source_bytes = SOURCE_BUILD.read_bytes()
    source_text = source_bytes.decode("utf-8")
    current_mac = mac_sources(source_text)

    already_patched = source_hash_before != PINNED_BASE_BUILD_SHA256
    reverse_result = None
    if not already_patched:
        before_bytes = source_bytes
        after_tree, after_build = make_tree("source-after", before_bytes)
        apply_result = apply_patch(after_tree)
        after_bytes = after_build.read_bytes()
    else:
        before_tree, before_build = make_tree("source-before", source_bytes)
        reverse_result = apply_patch(before_tree, reverse=True)
        before_bytes = before_build.read_bytes()
        if hashlib.sha256(before_bytes).hexdigest() != PINNED_BASE_BUILD_SHA256:
            raise AssertionError("reversing the patch did not recover the pinned source")
        after_tree, after_build = make_tree("source-after", before_bytes)
        apply_result = apply_patch(after_tree)
        after_bytes = after_build.read_bytes()
        if after_bytes != source_bytes:
            raise AssertionError("forward patch did not reproduce the existing patched source")

    before_text = before_bytes.decode("utf-8")
    after_text = after_bytes.decode("utf-8")
    before_selector = selector(before_text)
    after_selector = selector(after_text)
    before_mac = mac_sources(before_text)
    after_mac = mac_sources(after_text)
    if before_mac != after_mac or before_mac != current_mac:
        raise AssertionError("patch changed the separate macOS bundle target")
    if before_selector == after_selector:
        raise AssertionError("patch did not change the generic executable selector")
    late_selector = late_netbsd_selector(before_selector, after_selector)

    gn_version = command([GN, "--version"], WORK)
    fixture = WORK / "gn-fixture"
    stages = (("before", before_selector), ("after", after_selector),
              ("late-branch", late_selector))
    for stage, selected_text in stages:
        root = fixture / stage
        root.mkdir(parents=True, exist_ok=False)
        (root / ".gn").write_text('buildconfig = "//BUILDCONFIG.gn"\n')
        (root / "BUILDCONFIG.gn").write_text('''declare_args() {
  test_os = "linux"
}
current_os = test_os
''' + platforms + 'set_default_toolchain("//:default")\n')
        (root / "BUILD.gn").write_text(fixture_build(selected_text, before_mac))

    results = []
    selections = {}
    rejections = {}
    expected_common = {
        "linux": EXPECTED_LINUX, "freebsd": EXPECTED_LINUX,
        "openbsd": EXPECTED_LINUX, "win": EXPECTED_WIN,
        "winuwp": EXPECTED_WIN, "mac": before_mac,
        "chromeos": [], "android": [], "fuchsia": [], "ios": [],
        "watchos": [], "emscripten": [],
    }
    for stage, _ in stages:
        root = fixture / stage
        selections[stage] = {}
        for os_name in (("netbsd",) if stage == "late-branch" else OS_NAMES):
            result = run_gn(root, stage, os_name)
            actual = result["actual_sources"]
            if os_name == "netbsd":
                expected = EXPECTED_NETBSD if stage == "after" else EXPECTED_LINUX
            else:
                expected = expected_common[os_name]
            result["expected_sources"] = expected
            write_json(root / (stage + "-" + os_name + ".json"), result,
                       exclusive=False)
            require_sources(actual, expected)
            selections[stage][os_name] = actual
            results.append(result)
            if os_name == "netbsd" and stage != "after":
                rejections[stage] = reject_netbsd_sources(actual)
    for os_name in OS_NAMES:
        if os_name != "netbsd":
            require_sources(selections["after"][os_name],
                            selections["before"][os_name])

    source_hash_after = sha256_file(SOURCE_BUILD)
    if source_hash_after != source_hash_before:
        raise AssertionError("Electron source BUILD.gn changed during this test")
    config_hash_after = sha256_file(SOURCE_CONFIG)
    if config_hash_after != config_hash_before:
        raise AssertionError("Chromium BUILDCONFIG.gn changed during this test")
    summary = {
        "status": "PASS",
        "python": sys.version.split()[0],
        "sdk_api_version": emberbsd_sdk.API_VERSION,
        "sdk_module_origins": {module.__name__: str(Path(module.__file__).resolve())
                               for module in SDK_MODULES},
        "electron_source_build_gn_sha256_before": source_hash_before,
        "electron_source_build_gn_sha256_after": source_hash_after,
        "chromium_buildconfig_gn": str(SOURCE_CONFIG),
        "chromium_buildconfig_gn_sha256_before": config_hash_before,
        "chromium_buildconfig_gn_sha256_after": config_hash_after,
        "platform_assignments_sha256": sha256_file(WORK / "platform-assignments.gni"),
        "source_state": "already-patched" if already_patched else "baseline",
        "pinned_baseline_build_gn_sha256": PINNED_BASE_BUILD_SHA256,
        "patch_sha256": hashlib.sha256(PATCH.read_bytes()).hexdigest(),
        "gn": str(GN),
        "gn_version": gn_version["stdout"].strip(),
        "baseline_build_gn_sha256": hashlib.sha256(before_bytes).hexdigest(),
        "patched_fixture_build_gn_sha256": hashlib.sha256(after_bytes).hexdigest(),
        "patch_application_output": apply_result["stdout"],
        "patch_application": apply_result,
        "patch_reverse": reverse_result,
        "mac_bundle_sources": before_mac,
        "linux_sources_before_and_after": EXPECTED_LINUX,
        "windows_sources_before_and_after": EXPECTED_WIN,
        "netbsd_sources_before": EXPECTED_LINUX,
        "netbsd_sources_after": EXPECTED_NETBSD,
        "freebsd_sources_before_and_after": EXPECTED_LINUX,
        "openbsd_sources_before_and_after": EXPECTED_LINUX,
        "winuwp_sources_before_and_after": EXPECTED_WIN,
        "netbsd_posix_rejections": rejections,
        "selections": selections,
        "gn_fixture_count": len(results),
    }
    write_json(WORK / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


WORK.mkdir(parents=True, exist_ok=False)
main()
