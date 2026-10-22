#!/usr/bin/env python3.15
# Origin: EmberBSD (AI-assisted). GN host Node input regression.
"""Exercise Chromium's production Node input selectors for NetBSD cross builds."""
import sys

sys.dont_write_bytecode = True
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("use the selected host CPython 3.15")

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil

parser = argparse.ArgumentParser(description=__doc__)
for name in ("source", "gn", "sdk-source"):
    parser.add_argument("--" + name, required=True, type=Path)
parser.add_argument("new_work", type=Path, metavar="NEW_WORK")
args = parser.parse_args()
if not args.sdk_source.is_absolute() or not args.new_work.is_absolute():
    parser.error("SDK source and NEW_WORK must be absolute")
SOURCE, GN, SDK_SOURCE = (path.resolve(strict=True) for path in
                          (args.source, args.gn, args.sdk_source))
SDK_PACKAGE = SDK_SOURCE / "src/emberbsd_sdk"
if not (SDK_PACKAGE / "__init__.py").is_file():
    parser.error("selected SDK source has no emberbsd_sdk API")
sys.path.insert(0, str(SDK_SOURCE / "src"))
import emberbsd_sdk
if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error("selected SDK must provide API version 1")
if Path(emberbsd_sdk.__file__).resolve().parent != SDK_PACKAGE.resolve():
    parser.error("SDK package must come from selected source")
from emberbsd_sdk import errors, inventory, jsonio, process
SDK_MODULES = (emberbsd_sdk, errors, inventory, jsonio, process)
if any(not Path(module.__file__).resolve().is_relative_to(SDK_PACKAGE.resolve())
       for module in SDK_MODULES):
    parser.error("SDK modules must come from selected source")
CommandError = errors.CommandError
capture = process.capture
sha256_file = inventory.sha256_file
write_json = jsonio.write_json

ROOT = args.new_work.resolve()
if ROOT.exists():
    parser.error("NEW_WORK must not already exist")
if ROOT.is_relative_to(SOURCE) or ROOT.is_relative_to(SDK_SOURCE):
    parser.error("NEW_WORK must be outside Chromium source and selected SDK")
PATCH = Path(__file__).resolve().parent.parent / "patches/gn-host-node-inputs.patch"
PATCH = PATCH.resolve(strict=True)
NODE_SCRIPT = SOURCE / "third_party/node/node.py"
PROTO_FILE = SOURCE / "third_party/protobuf/proto_library.gni"
NODE_GNI = SOURCE / "third_party/node/node.gni"
for path in (SOURCE, GN, PATCH, NODE_SCRIPT, PROTO_FILE, NODE_GNI):
    if not path.exists():
        parser.error("required input is missing: " + str(path))
SOURCE_INPUTS = (PROTO_FILE, NODE_GNI, SOURCE / "third_party/node/update_node_binaries",
                 NODE_SCRIPT, SOURCE / "build/toolchain/rbe.gni",
                 SOURCE / "build/toolchain/siso.gni",
                 SOURCE / "build/config/gclient_args.gni",
                 SOURCE / "build/toolchain/check_rewrapper_cfg.py")
SOURCE_HASHES_BEFORE = {str(path): sha256_file(path) for path in SOURCE_INPUTS}
if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
    parser.error("this regression requires its intended macOS arm64 GN host")
PATCH_TOOL = shutil.which("patch")
if PATCH_TOOL is None:
    parser.error("POSIX patch is required to verify the carried patch")

ROOT.mkdir(parents=True, exist_ok=False)
LOGS = ROOT / "logs"
LOGS.mkdir()
PYTHON_TOOLS = ROOT / "python-bin"
PYTHON_TOOLS.mkdir()
(PYTHON_TOOLS / "python").symlink_to(Path(sys.executable).resolve(strict=True))
commands = []
environment = {"PATH": str(PYTHON_TOOLS) + os.pathsep + os.defpath,
               "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}


def run(name, command, *, cwd, expected_status=0):
    argv = list(map(str, command))
    try:
        result = capture(argv, cwd=cwd, env=environment)
        status, stdout, stderr = result.returncode, result.stdout, result.stderr
    except CommandError as error:
        status, stdout, stderr = error.returncode, error.stdout, error.stderr
    (LOGS / (name + ".stdout")).write_bytes(stdout)
    (LOGS / (name + ".stderr")).write_bytes(stderr)
    commands.append(dict(name=name, argv=argv, cwd=str(cwd), status=status))
    write_json(LOGS / "commands.json", commands, exclusive=False)
    if status != expected_status:
        raise AssertionError((name, status, stdout[-4000:], stderr[-4000:]))
    return stdout.decode("utf-8", "strict")


def copy_pair(destination, from_root):
    for relative in ("third_party/protobuf/proto_library.gni",
                     "third_party/node/node.gni"):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(from_root / relative, target)


def patch_pair(tree, reverse=False):
    flags = [PATCH_TOOL, "-p1", "-F", "0", "-i", PATCH]
    if reverse:
        flags.insert(1, "-R")
    run(("patch-reverse-" if reverse else "patch-forward-") + tree.name,
        flags, cwd=tree)

# Detect whether this input checkout already contains the patch. Apply or reverse
# only in the private work directory, then verify both exact resulting files.
seed = ROOT / "seed"
copy_pair(seed, SOURCE)
# Classify the source by its exact selector signatures. The patch itself is
# applied or reversed only in the private fixture below.
proto_text = (SOURCE / "third_party/protobuf/proto_library.gni").read_text()
node_text = (SOURCE / "third_party/node/node.gni").read_text()
source_is_after = ('if (host_os == "netbsd") {' in proto_text and
                   'if (host_os == "mac") {' in node_text and
                   'if (host_os == "linux" || use_remoteexec) {' in node_text)
source_is_before = ('if (is_netbsd) {' in proto_text and
                    'if (is_mac && host_os == "mac") {' in node_text and
                    'if ((is_linux || is_chromeos || use_remoteexec) && !is_bsd) {' in node_text)
if source_is_before == source_is_after:
    raise SystemExit("source files are mixed or have unknown Node selector state")
source_state = "after" if source_is_after else "before"
if source_is_after:
    patch_pair(seed, reverse=True)
    before_root = seed
    after_root = ROOT / "after-source"
    copy_pair(after_root, SOURCE)
    # Check that the pinned after-source is exactly reproducible from baseline.
    forward = ROOT / "forward-check"
    copy_pair(forward, before_root)
    patch_pair(forward)
    for relative in ("third_party/protobuf/proto_library.gni", "third_party/node/node.gni"):
        assert (forward / relative).read_bytes() == (after_root / relative).read_bytes(), relative
else:
    before_root = seed
    after_root = ROOT / "after"
    copy_pair(after_root, before_root)
    patch_pair(after_root)

proto_before = (before_root / "third_party/protobuf/proto_library.gni").read_text()
proto_after = (after_root / "third_party/protobuf/proto_library.gni").read_text()
node_before = (before_root / "third_party/node/node.gni").read_text()
node_after = (after_root / "third_party/node/node.gni").read_text()


def proto_selector(text):
    start = text.index("if (is_openbsd) {") if "if (is_openbsd) {" in text else text.index('if (host_os == "openbsd") {')
    end = text.index('\ntemplate("proto_library")', start)
    return text[start:end].strip()


def node_selector(text):
    start = text.index("    # Declare dependencies to all involved tools.")
    end = text.index('    # Automatically add a dependency to ":check_version"', start)
    return text[start:end].rstrip()

PROTO_BEFORE = proto_selector(proto_before)
PROTO_AFTER = proto_selector(proto_after)
NODE_BEFORE = node_selector(node_before)
NODE_AFTER = node_selector(node_after)

# Confirm the host Node pin and host-selection helper without changing either.
version_file = SOURCE / "third_party/node/update_node_binaries"
match = re.search(r'^NODE_VERSION="(v[0-9.]+)"$', version_file.read_text(), re.MULTILINE)
if not match:
    raise SystemExit("cannot identify Chromium's pinned Node version")
expected_node_version = match.group(1)
spec = importlib.util.spec_from_file_location("e12_node_path_probe", NODE_SCRIPT)
node_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(node_module)
node_binary = Path(node_module.GetBinaryPath()).resolve(strict=True)
expected_node_rel = Path("third_party/node/mac_arm64/node-darwin-arm64/bin/node")
if not node_binary.is_relative_to(SOURCE) or node_binary.relative_to(SOURCE) != expected_node_rel:
    raise SystemExit("node.py did not select the pinned macOS arm64 host Node")
SOURCE_INPUTS += (node_binary,)
SOURCE_HASHES_BEFORE[str(node_binary)] = sha256_file(node_binary)
node_version = run("node-version", [node_binary, "--version"], cwd=SOURCE).strip()
if node_version != expected_node_version:
    raise SystemExit(f"pinned Node mismatch: {node_version} != {expected_node_version}")


CONFIG = '''declare_args() {
  fixture_remoteexec = false
  fixture_host_os = host_os
  fixture_host_cpu = host_cpu
}
if (target_os == "") { target_os = host_os }
if (target_cpu == "") { target_cpu = host_cpu }
current_os = target_os
current_cpu = target_cpu
is_openbsd = current_os == "openbsd"
is_freebsd = current_os == "freebsd"
is_netbsd = current_os == "netbsd"
is_bsd = is_openbsd || is_freebsd || is_netbsd
is_linux = current_os == "linux"
is_chromeos = current_os == "chromeos"
is_win = current_os == "win"
is_mac = current_os == "mac"
host_toolchain = "//:default"
set_default_toolchain("//:default")
TESTONLY_AND_VISIBILITY = [ "testonly", "visibility" ]
'''
ROOT_BUILD = 'toolchain("default") {}\n'


def selector_fixture(name, selector, *, host_os=None, host_cpu=None, remote=False,
                     target_os="netbsd"):
    tree = ROOT / name / "src"
    out = ROOT / name / "out"
    tree.mkdir(parents=True)
    out.mkdir(parents=True)
    (tree / ".gn").write_text('buildconfig = "//BUILDCONFIG.gn"\n')
    (tree / "BUILDCONFIG.gn").write_text(CONFIG + "use_remoteexec = fixture_remoteexec\n")
    (tree / "BUILD.gn").write_text(
        ROOT_BUILD + '\n_protoc_gen_ts_runtime_deps = []\n' + selector +
        '\nprobe_node_deps = _protoc_gen_ts_runtime_deps\n'
        'action("probe") {\n'
        '  script = "//probe.py"\n'
        '  inputs = probe_node_deps\n'
        '  outputs = [ "$target_gen_dir/probe.out" ]\n'
        '}\n')
    (tree / "probe.py").write_text("# GN planning fixture; never executed.\n")
    args_lines = [f'target_os = "{target_os}"', 'target_cpu = "arm64"',
                  f'fixture_remoteexec = {str(remote).lower()}']
    if host_os is not None:
        # Built-in GN host values are immutable. Only selector expressions in
        # this logic fixture are substituted; label the result simulated.
        build_text = (tree / "BUILD.gn").read_text()
        build_text = build_text.replace("host_os", "fixture_host_os").replace("host_cpu", "fixture_host_cpu")
        (tree / "BUILD.gn").write_text(build_text)
        args_lines.extend((f'fixture_host_os = "{host_os}"',
                           f'fixture_host_cpu = "{host_cpu or "x64"}"'))
    (out / "args.gn").write_text("\n".join(args_lines) + "\n")
    run(name + "-gn-gen", [GN, "gen", out], cwd=tree)
    output = run(name + "-gn-desc", [GN, "desc", out, "//:probe", "inputs"], cwd=tree)
    return {line.strip() for line in output.splitlines()
            if line.strip().startswith("//third_party/node/") and
            (line.strip().endswith("/bin/node") or line.strip().endswith("/node.exe"))}


def expect_inputs(name, actual, expected):
    if actual != set(expected):
        raise AssertionError(f"{name}: selected {sorted(actual)}, expected {sorted(expected)}")

node_mac = "//third_party/node/mac_arm64/node-darwin-arm64/bin/node"
node_linux = "//third_party/node/linux/node-linux-x64/bin/node"
node_netbsd = "//third_party/node/netbsd/node-netbsd/bin/node"
node_freebsd = "//third_party/node/freebsd/node-freebsd/bin/node"
node_openbsd = "//third_party/node/openbsd/node-openbsd/bin/node"
node_windows = "//third_party/node/win/node.exe"

# Baseline reproduces the actual macOS-host / NetBSD-target misdeclaration.
expect_inputs("before-mac-netbsd", selector_fixture("proto-before-mac-netbsd", PROTO_BEFORE),
              {node_netbsd})
expect_inputs("after-mac-netbsd", selector_fixture("proto-after-mac-netbsd", PROTO_AFTER),
              {node_mac})
expect_inputs("before-mac-netbsd-remote", selector_fixture(
    "proto-before-mac-netbsd-remote", PROTO_BEFORE, remote=True), {node_netbsd})
expect_inputs("after-mac-netbsd-remote", selector_fixture(
    "proto-after-mac-netbsd-remote", PROTO_AFTER, remote=True), {node_mac, node_linux})

# Simulated host cases exercise the selector logic only; they do not claim to
# execute GN or Node on these operating systems.
for host, target, expected in (
    ("netbsd", "netbsd", {node_netbsd}),
    ("freebsd", "freebsd", {node_freebsd}),
    ("openbsd", "openbsd", {node_openbsd}),
    ("linux", "netbsd", {node_linux}),
    ("win", "netbsd", {node_windows}),
):
    label = f"simulated-{host}-host-target-{target}"
    expect_inputs(label, selector_fixture("proto-" + label, PROTO_AFTER,
                                          host_os=host, target_os=target), expected)


def node_template_fixture(name, source_text, *, simulated_host=None,
                          target_os="netbsd", remote=False):
    tree = ROOT / name / "src"
    out = ROOT / name / "out"
    tree.mkdir(parents=True)
    out.mkdir(parents=True)
    for relative in ("build/config/gclient_args.gni", "build/toolchain/rbe.gni",
                     "build/toolchain/siso.gni", "build/toolchain/check_rewrapper_cfg.py"):
        target = tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / relative, target)
    (tree / ".gn").write_text('buildconfig = "//BUILDCONFIG.gn"\n')
    (tree / "BUILDCONFIG.gn").write_text(CONFIG)
    (tree / "BUILD.gn").write_text(
        ROOT_BUILD + 'group("all") { deps = [ "//third_party/node:check_version" ] }\n')
    node_dir = tree / "third_party/node"
    node_dir.mkdir(parents=True)
    if simulated_host:
        source_text = source_text.replace("host_os", "fixture_host_os").replace("host_cpu", "fixture_host_cpu")
    (node_dir / "node.gni").write_text(source_text)
    (node_dir / "BUILD.gn").write_text(
        'import("//third_party/node/node.gni")\n'
        'node("check_version") {\n'
        '  script = "check_version.py"\n'
        '  inputs = []\n'
        '  outputs = [ "$target_gen_dir/check_version_result.txt" ]\n'
        '}\n')
    (node_dir / "check_version.py").write_text("# GN planning fixture; never executed.\n")
    args_lines = [f'target_os = "{target_os}"', 'target_cpu = "arm64"',
                  f'use_remoteexec = {str(remote).lower()}']
    if remote:
        args_lines.append('use_siso = true')
        config = tree / "buildtools/reclient_cfgs/chromium-browser-clang/rewrapper_mac.cfg"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text("fixture-only config existence marker; no remote action runs\n")
    if simulated_host:
        args_lines.extend((f'fixture_host_os = "{simulated_host}"',
                           'fixture_host_cpu = "x64"'))
    (out / "args.gn").write_text("\n".join(args_lines) + "\n")
    run(name + "-gn-gen", [GN, "gen", out], cwd=tree)
    output = run(name + "-gn-desc", [GN, "desc", out, "//third_party/node:check_version", "inputs"], cwd=tree)
    return {line.strip() for line in output.splitlines()
            if line.strip().startswith("//third_party/node/") and
            (line.strip().endswith("/bin/node") or line.strip().endswith("/node.exe"))}

# This fixture imports the complete production node.gni and its actual GN helper
# imports. It proves that the checked-in template adds the pinned host Node.
expect_inputs("template-before-mac-netbsd",
              node_template_fixture("template-before-mac-netbsd", node_before), set())
expect_inputs("template-after-mac-netbsd",
              node_template_fixture("template-after-mac-netbsd", node_after), {node_mac})
expect_inputs("template-before-mac-netbsd-remote",
              node_template_fixture("template-before-mac-netbsd-remote", node_before,
                                    remote=True), set())
expect_inputs("template-after-mac-netbsd-remote",
              node_template_fixture("template-after-mac-netbsd-remote", node_after,
                                    remote=True), {node_mac, node_linux})
for host, expected in (("linux", {node_linux}), ("win", {node_windows})):
    label = f"template-simulated-{host}-host-netbsd-target"
    expect_inputs(label, node_template_fixture("template-" + label, node_after,
                                               simulated_host=host), expected)

# The Mac binary must match Chromium's own update script pin, not a separate
# Electron/ASAR helper runtime.
for inputs in (PROTO_AFTER, NODE_AFTER):
    if node_mac not in inputs:
        raise AssertionError("patched production selector does not mention pinned Mac Node")
if not node_binary.is_file():
    raise AssertionError("pinned Mac Node executable is missing")

source_hashes_after = {str(path): sha256_file(path) for path in SOURCE_INPUTS}
if source_hashes_after != SOURCE_HASHES_BEFORE:
    raise SystemExit("source inputs changed while the regression was running")
receipt = dict(
    status="PASS",
    source=str(SOURCE), source_state=source_state,
    patch=str(PATCH), patch_sha256=sha256_file(PATCH),
    gn=str(GN), gn_version=run("gn-version", [GN, "--version"], cwd=SOURCE).strip(),
    sdk_source=str(SDK_SOURCE), sdk_api=1,
    sdk_sha256={str(module.__file__): sha256_file(module.__file__) for module in SDK_MODULES},
    source_sha256=source_hashes_after,
    node_version_pin=expected_node_version, node_version=node_version,
    node_binary=str(node_binary), node_binary_sha256=sha256_file(node_binary),
    simulated_host_cases=["NetBSD", "FreeBSD", "OpenBSD", "Linux", "Windows"],
    scope="GN planning fixtures only. The Mac/NetBSD baseline failure, production selectors, pinned host Node input and remote Linux input are checked. Remoteexec fixtures use only a synthetic rewrapper config file to pass GN's existence check; no remote action runs. Simulated host OS cases only evaluate selector logic. No target objects, full Chromium graph, or application runtime are built or executed.",
    commands=commands)
write_json(ROOT / "result.json", receipt)
print(json.dumps(dict(status="PASS", source_state=source_state,
                      gn_cases=len([item for item in commands if item["name"].endswith("-gn-gen")]),
                      node_version=node_version, node_sha256=receipt["node_binary_sha256"],
                      result=str(ROOT / "result.json")), indent=2))
