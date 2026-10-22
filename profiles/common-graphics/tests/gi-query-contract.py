#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), ported from the EmberBSD Ruby regression.
"""Check real ELF fixtures and bounded mocked transport. No target execution."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys

TARGETS = {"aarch64": ("aarch64", "aarch64--netbsd", 183),
           "amd64": ("x86_64", "x86_64--netbsd", 62)}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def environment(changes):
    result = os.environ.copy()
    for key, value in changes.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = str(value)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS, default="aarch64")
    parser.add_argument("--recipe", type=Path,
                        default=Path(__file__).resolve().parent.parent /
                        "recipes/devel/gobject-introspection")
    parser.add_argument("cross_tools", type=Path)
    parser.add_argument("work", type=Path)
    args = parser.parse_args()
    python = Path(os.environ.get("EMBERBSD_TEST_PYTHON", sys.executable))
    require(python.is_absolute() and python.is_file() and os.access(python, os.X_OK),
            "EMBERBSD_TEST_PYTHON must name an absolute executable")
    python = python.resolve(strict=True)
    processor, triplet, machine = TARGETS[args.target]
    cc = (args.cross_tools / "bin" / (triplet + "-gcc")).resolve(strict=True)
    readelf = (args.cross_tools / "bin" / (triplet + "-readelf")).resolve(strict=True)
    require(args.work.is_absolute() and not os.path.lexists(args.work), "new absolute work required")
    args.work.mkdir(parents=True)
    work = args.work.resolve(strict=True)
    for name in ("build/provider", "sysroot", "cache", "bin", "outside"):
        (work / name).mkdir(parents=True)
    recipe = args.recipe.resolve(strict=True)
    helper = recipe / "files/target-query.py"
    needed = recipe / "files/elf-needed.sh"
    inputs = {str(p): digest(p) for p in (helper, needed, recipe / "cross.mk")}
    commands = []

    def capture(name, command, env=None, *, data=None, separate=False):
        argv = [str(item) for item in command]
        result = subprocess.run(argv, env=environment(env or {}), input=data,
                                text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE if separate else subprocess.STDOUT,
                                timeout=60)
        (work / (name + ".log")).write_text(result.stdout + (result.stderr or ""))
        commands.append({"name": name, "argv": argv, "returncode": result.returncode})
        return result

    def run(name, command, env=None, **options):
        result = capture(name, command, env, **options)
        require(result.returncode == 0, name + ": " + result.stdout + (result.stderr or ""))
        return result.stdout

    run("native-python-version", [python, "--version"])
    (work / "native-python-provider.json").write_text(json.dumps(
        {"path": str(python), "sha256": digest(python)}, indent=2) + "\n")
    run("compiler-version", [cc, "--version"])
    (work / "build/library.c").write_text("int gi_probe_answer(void) { return 42; }\n")
    (work / "build/query.c").write_text("extern int gi_probe_answer(void); void _start(void) { (void)gi_probe_answer(); }\n")
    run("dso", [cc, "-nostdlib", "-shared", "-fPIC", work / "build/library.c",
                "-Wl,-soname,libgi-probe.so.1", "-o", work / "build/provider/libgi-probe.so.1"])
    run("elf", [cc, "-nostdlib", "-Wl,-e,_start", work / "build/query.c",
                "-L" + str(work / "build/provider"), "-Wl,-l:libgi-probe.so.1",
                "-o", work / "build/query"])
    (work / "provider-alias").symlink_to(work / "build/provider")
    marker = work / "ssh-reached"
    ssh = work / "bin/ssh"
    ssh.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\" > " + shlex.quote(str(work / "ssh-arguments")) +
                   "\nprintf '%s\\n' reached >> " + shlex.quote(str(marker)) + "\nexit 74\n")
    ssh.chmod(0o755)
    config = {"build_root": str(work / "build"), "sysroot": str(work / "sysroot"),
              "cache": str(work / "cache"), "readelf": str(readelf), "ssh": "unused.invalid",
              "library_dirs": [str(work / "provider-alias")]}
    if args.target != "aarch64":
        config["target"] = args.target
    config_path = work / "config.json"

    def save_config(value):
        config_path.write_text(json.dumps(value, indent=2) + "\n")

    save_config(config)
    env = {"EMBERBSD_GI_QUERY_CONFIG": str(config_path), "PATH": str(work / "bin") + ":/usr/bin:/bin",
           "LD_LIBRARY_PATH": None, "DYLD_LIBRARY_PATH": None, "LD_PRELOAD": None}

    def reject(name, pattern, *arguments, extra_env=None):
        result = capture(name, [python, helper, *arguments], env | (extra_env or {}))
        require(result.returncode != 0 and re.search(pattern, result.stdout) and not marker.exists(),
                name + " did not fail at expected boundary: " + result.stdout)

    run("check", [python, helper, "--check", work / "build", work / "sysroot", readelf, args.target], env)
    # Real bmake checks both metadata sets, not both target toolchains or a VM.
    make_tree = work / "make"
    make_recipe = make_tree / "devel/gobject-introspection"
    make_recipe.mkdir(parents=True)
    (make_tree / "mk").mkdir()
    (make_tree / "mk/bsd.prefs.mk").write_text("")
    shutil.copyfile(recipe / "cross.mk", make_recipe / "cross.mk")
    (make_recipe / "Makefile").write_text('.include "cross.mk"\n')
    make_base = [os.environ.get("BMAKE", "bmake"), "-C", make_recipe,
                 "USE_CROSS_COMPILE=yes", "OPSYS=NetBSD", "CROSS_OPSYS=NetBSD", "CROSS_OS_VERSION=11.0",
                 "EMBERBSD_GI_PYTHON=" + str(python), "EMBERBSD_GI_QUERY_CONFIG=" + str(config_path),
                 "EMBERBSD_CROSS_BUILD_CC=/usr/bin/cc", "TOOLDIR=" + str(args.cross_tools)]
    for selected, (arch, gnu, _) in reversed(TARGETS.items()):
        settings = ["MACHINE_ARCH=" + arch, "CROSS_MACHINE_ARCH=" + arch,
                    "MACHINE_GNU_PLATFORM=" + gnu, "EMBERBSD_CROSS_TARGET=" + selected]
        reason = run("make-" + selected, [*make_base, *settings, "-V", "${PKG_FAIL_REASON}"])
        require(not reason.strip(), "supported GI target rejected: " + reason)
        settings_env = run("make-env-" + selected, [*make_base, *settings, "-V", "${MAKE_ENV}"])
        require("/bin/" + gnu + "-readelf" in settings_env and "EMBERBSD_GI_TARGET=" + selected in settings_env
                and "target-query.py" in settings_env and str(python) in settings_env,
                "GI selected a foreign target readelf/environment")
        foreign = "x86_64" if arch == "aarch64" else "aarch64"
        reason = run("make-mixed-" + selected,
                     [*make_base, *settings, "CROSS_MACHINE_ARCH=" + foreign, "-V", "${PKG_FAIL_REASON}"])
        require(reason.strip(), "GI accepted mixed architecture metadata")
        reason = run("make-mixed-gnu-" + selected,
                     [*make_base, *settings, "MACHINE_GNU_PLATFORM=foreign--netbsd", "-V", "${PKG_FAIL_REASON}"])
        require(reason.strip(), "GI accepted a foreign GNU provider")
    save_config(config | {"host_key_alias": "unsafe alias"})
    reject("invalid-host-alias", "invalid host key alias", "--check", work / "build", work / "sysroot", readelf)
    config["host_key_alias"] = "target.example"
    save_config(config)
    reject("different-sysroot", "configuration differs", "--check", work / "build", work / "outside", readelf)
    reject("outside-binary", "outside build root", "/usr/bin/true")
    shutil.copyfile("/usr/bin/true", work / "build/native")
    reject("native-binary", "not little-endian .* ELF64", work / "build/native")
    other_target = "amd64" if args.target == "aarch64" else "aarch64"
    save_config(config | {"target": other_target})
    reject("foreign-query-config", "configuration differs|not little-endian .* ELF64", "--check",
           work / "build", work / "sysroot", readelf, args.target)
    reject("foreign-query-architecture", "not little-endian .* ELF64", work / "build/query")
    legacy = config.copy()
    legacy.pop("target", None)
    save_config(legacy)
    if args.target == "amd64":
        reject("legacy-is-not-amd64", "configuration differs", "--check", work / "build", work / "sysroot", readelf, args.target)
    run("legacy-aarch64-check", [python, helper, "--check", work / "build", work / "sysroot", readelf], env)
    save_config(config | {"target": "unsupported"})
    reject("unknown-target", "unsupported GI target", "--check", work / "build", work / "sysroot", readelf)
    save_config(config)
    provider = work / "build/provider/libgi-probe.so.1"
    original = provider.read_bytes()
    foreign = bytearray(original)
    struct.pack_into("<H", foreign, 18, 183 if machine == 62 else 62)
    provider.write_bytes(foreign)
    reject("foreign-provider", "not little-endian .* ELF64", work / "build/query")
    for name, offset, value in (("foreign-class", 4, 1), ("foreign-endian", 5, 2)):
        foreign = bytearray(original)
        foreign[offset] = value
        provider.write_bytes(foreign)
        reject(name, "not little-endian .* ELF64", work / "build/query")
    provider.write_bytes(original)
    reject("unsupported-args", "only an optional", work / "build/query", "--delete")
    (work / "build/types").write_text("get-type:gi_probe_answer\n")
    (work / "outside/untouched").write_text("unchanged")
    (work / "build/output").symlink_to(work / "outside/untouched")
    reject("output-symlink", "output already exists", work / "build/query",
           "--introspect-dump=" + str(work / "build/types") + "," + str(work / "build/output"))
    require((work / "outside/untouched").read_text() == "unchanged", "symlink target modified")
    save_config(config | {"library_dirs": []})
    reject("missing-provider", "missing provider: libgi-probe.so.1", work / "build/query")
    save_config(config | {"sysroot": str(work / "build")})
    reject("overlapping-roots", "build/sysroot overlap", "--check", work / "build", work / "build", readelf)
    save_config(config)
    result = capture("valid-alias", [python, helper, work / "build/query"], env)
    require(result.returncode != 0 and "allocate failed (74)" in result.stdout and marker.read_text() == "reached\n",
            "valid target/alias did not reach bounded transport")
    allocation = (work / "ssh-arguments").read_text().splitlines()[-1]
    require('test "$(uname -s)" = NetBSD' in allocation and 'test "$(uname -p)" = ' + processor in allocation,
            "selected target uname contract missing")
    marker.unlink()
    result = capture("execute-args", [python, helper, "--execute", work / "build/query", "two words", "single'quote", ""], env)
    require(result.returncode != 0 and "allocate failed (74)" in result.stdout and marker.read_text() == "reached\n",
            "execute argv did not reach bounded transport")
    marker.unlink()

    def reject_command(name, pattern, *arguments):
        failure = work / ("build/" + name + "-failure")
        reject(name, pattern, *arguments, extra_env={"EMBERBSD_GI_FAILURE_MARKER": str(failure)})
        require(failure.is_file(), name + " left no failure marker")

    reject_command("missing-command", "target command missing from sysroot: getconf", "--execute", "getconf", "LFS_CFLAGS")
    (work / "sysroot/usr/bin").mkdir(parents=True)
    (work / "sysroot/bin").mkdir()
    shutil.copyfile(work / "build/query", work / "sysroot/bin/sh")
    (work / "sysroot/usr/bin/getconf").symlink_to("../../bin/sh")
    reject_command("symlinked-command", "not a sysroot regular file: getconf", "--execute", "getconf", "LFS_CFLAGS")
    (work / "sysroot/usr/bin/getconf").unlink()
    shutil.copyfile(work / "build/query", work / "sysroot/usr/bin/getconf")
    reject("command-without-execute", "unsupported target command: getconf", "getconf")
    reject_command("unlisted-command", "unsupported target command: sh", "--execute", "sh", "-c", "true")
    before = set((work / "cache").glob("gi-query-*"))
    result = capture("execute-getconf", [python, helper, "--execute", "getconf", "LFS_CFLAGS"], env)
    require(result.returncode != 0 and "allocate failed (74)" in result.stdout and marker.read_text() == "reached\n",
            "sysroot getconf did not reach bounded transport")
    created = set((work / "cache").glob("gi-query-*")) - before
    require(len(created) == 1, "missing getconf receipt")
    getconf = work / "sysroot/usr/bin/getconf"
    receipt = digest(getconf) + "  " + str(getconf)
    require(receipt in (created.pop() / "sources.sha256").read_text().splitlines(), "getconf receipt names another program")
    print("PASS: execute mode runs only the sysroot getconf for target commands")
    # Run the production identity shell body with explicit host fixtures.
    identity_marker = work / "identity-allocated"
    identity_glue = ('uname() { case "$1" in -s) printf \'%s\\n\' "$GI_FIXTURE_OPSYS";; '
                     '-p) printf \'%s\\n\' "$GI_FIXTURE_PROCESSOR";; *) return 2;; esac; }\n'
                     'mktemp() { printf \'allocated\\n\' > ' + shlex.quote(str(identity_marker)) +
                     '; printf \'/tmp/ember-gir.AbCd1234\\n\'; }\n')
    for opsys, arch, accepted in (("NetBSD", processor, True),
                                  ("NetBSD", "x86_64" if processor == "aarch64" else "aarch64", False),
                                  ("Linux", processor, False)):
        identity_marker.unlink(missing_ok=True)
        result = capture("identity-" + opsys + "-" + arch, ["sh", "-s"],
                         {"GI_FIXTURE_OPSYS": opsys, "GI_FIXTURE_PROCESSOR": arch}, data=identity_glue + allocation)
        require((result.returncode == 0) == accepted and identity_marker.exists() == accepted,
                "remote identity did not gate allocation")
    needed_env = {"EMBERBSD_GI_READELF": str(readelf), "EMBERBSD_GI_TARGET": args.target}
    require(run("needed", ["sh", needed, work / "build/query"], needed_env) == "libgi-probe.so.1\n", "wrong target SONAME")
    require(capture("needed-native", ["sh", needed, work / "build/native"], needed_env).returncode != 0,
            "native image accepted by SONAME helper")
    require(capture("needed-foreign", ["sh", needed, work / "build/query"],
                    needed_env | {"EMBERBSD_GI_TARGET": other_target}).returncode != 0,
            "foreign machine accepted by SONAME helper")
    for invalid in ("", "unsupported"):
        result = capture("needed-" + (invalid or "empty"), ["sh", needed, work / "build/query"],
                         needed_env | {"EMBERBSD_GI_TARGET": invalid})
        require(result.returncode != 0 and "unsupported GI target" in result.stdout,
                "empty or unknown SONAME target did not fail closed")
    print("PASS: both target make metadata sets, JSON targets, foreign ELF/class/endian and production identity shell guard")
    # Inject transport outcomes; never execute the cross-built program.
    ssh.write_text("#!" + str(python) + "\n" + r'''
import os
from pathlib import Path
import sys
command = sys.argv[-1]
mode = os.environ["GI_TEST_MODE"]
if "mktemp" in command: phase = "allocate"
elif command.startswith("tar "): phase = "transfer"
elif command == "sh -s -- ember-gir-reuse": phase = "reuse"
elif command == "sh -s": phase = "query"
elif command.startswith("cat ") and "execution.status" in command: phase = "status"
elif command.startswith("test -s "): phase = "readback"
elif command.startswith("rm -rf "): phase = "cleanup"
else: sys.exit("unexpected test transport command")
with open(os.environ["GI_TEST_PHASES"], "a") as stream: stream.write(phase + "\n")
if phase in ("transfer", "query", "reuse"): sys.stdin.buffer.read()
if mode == phase: sys.exit(74)
if phase == "allocate": print("/tmp/ember-gir.AbCd1234")
elif phase == "reuse":
    if mode == "reuse-unknown": print("unexpected.so")
    if mode == "reuse-duplicate": print("libgi-probe.so.1\nlibgi-probe.so.1")
    if mode == "reused": print("libgi-probe.so.1")
elif phase == "query":
    if mode.startswith("execute-"):
        sys.stdout.write("probe stdout\n")
        sys.stderr.write("probe stderr\n")
        sys.exit(7 if mode == "execute-fail" else 0)
    if mode == "input-change": Path(os.environ["GI_TEST_INPUT"]).write_text("modified")
elif phase == "status": print("7" if mode == "execute-fail" else "0")
elif phase == "readback": print("not XML" if mode == "bad-xml" else "<dump></dump>")
''')
    (work / "build/output").unlink()
    (work / "sysroot/usr/pkg/lib").mkdir(parents=True)
    installed = work / "sysroot/usr/pkg/lib/libgi-probe.so.1"
    shutil.copyfile(provider, installed)
    save_config(config | {"library_dirs": [str(installed.parent)]})
    expected = {
        "reuse": ("allocate reuse cleanup", "reuse failed"),
        "reuse-unknown": ("allocate reuse cleanup", "invalid reused library response"),
        "reuse-duplicate": ("allocate reuse cleanup", "invalid reused library response"),
        "reused": ("allocate reuse transfer query readback cleanup", None),
        "transfer": ("allocate reuse transfer cleanup", "transfer failed"),
        "query": ("allocate reuse transfer query cleanup", "target query failed"),
        "readback": ("allocate reuse transfer query readback cleanup", "invalid introspection XML"),
        "bad-xml": ("allocate reuse transfer query readback cleanup", "invalid introspection XML"),
        "cleanup": ("allocate reuse transfer query readback cleanup", "remote cleanup failed"),
        "input-change": ("allocate reuse transfer query readback cleanup", "source providers changed"),
        "success": ("allocate reuse transfer query readback cleanup", None),
    }
    for mode, (phases, error) in expected.items():
        (work / "build/types").write_text("original type query\n")
        trace = work / (mode + "-phases.txt")
        outcome = work / ("build/" + mode + ".xml")
        transport_env = env | {"GI_TEST_MODE": mode, "GI_TEST_PHASES": str(trace), "GI_TEST_INPUT": str(work / "build/types")}
        result = capture("transport-" + mode, [python, helper, work / "build/query",
                         "--introspect-dump=" + str(work / "build/types") + "," + str(outcome)], transport_env)
        require(trace.read_text().split() == phases.split(), mode + ": wrong transport phases")
        if error:
            require(result.returncode != 0 and re.search(error, result.stdout), mode + ": wrong failure boundary: " + result.stdout)
            require(not outcome.exists(), mode + ": published failed output")
        else:
            require(result.returncode == 0 and outcome.read_text() == "<dump></dump>\n", mode + ": valid output missing: " + result.stdout)
    # Run the production reuse shell body with local paths and a host SHA command.
    reuse_body = next((work / "cache").glob("*/reuse.sh")).read_text()
    reuse_root = work / "reuse-shell"
    body = reuse_body.replace("/tmp/ember-gir.AbCd1234", str(reuse_root)).replace("/usr/pkg/lib/libgi-probe.so.1", str(installed))
    sha_glue = 'sha256() { test "$1" = -q || return 2; shift; /usr/bin/shasum -a 256 "$1" | cut -d " " -f 1; }\n'
    for mode in ("matched", "changed", "missing", "corrupted-copy"):
        if reuse_root.exists():
            shutil.rmtree(reuse_root)
        reuse_root.mkdir()
        shutil.copyfile(provider, installed)
        if mode == "changed":
            installed.write_text("different installed file")
        if mode == "missing":
            installed.unlink()
        corruption = 'cp() { /bin/cp "$1" "$2" && printf corrupted >> "$2"; }\n' if mode == "corrupted-copy" else ""
        result = capture("reuse-shell-" + mode, ["sh", "-s"], data=sha_glue + corruption + body)
        copied = reuse_root / "lib/libgi-probe.so.1"
        if mode == "matched":
            require(result.returncode == 0 and result.stdout == "libgi-probe.so.1\n" and digest(copied) == digest(installed),
                    "reuse did not copy matching provider")
        elif mode in ("changed", "missing"):
            require(result.returncode == 0 and not result.stdout and not copied.exists(), "reuse did not fall back to transfer")
        else:
            require(result.returncode == 92 and not result.stdout, "reuse accepted corrupt copied bytes")
    print("PASS: production reuse shell copies identical bytes, falls back for missing/changed files and rejects corruption")
    for mode in ("execute-pass", "execute-fail"):
        phases = work / (mode + "-phases")
        result = capture(mode, [python, helper, "--execute", work / "build/query"],
                         env | {"GI_TEST_MODE": mode, "GI_TEST_PHASES": str(phases)}, separate=True)
        require(result.stdout == "probe stdout\n" and result.stderr == "probe stderr\n" and
                result.returncode == (7 if mode == "execute-fail" else 0), mode + ": lost probe streams/status")
        require(phases.read_text().splitlines() == "allocate reuse transfer query status cleanup".split(), mode + ": missing cleanup")
    for mode in ("query", "status", "cleanup"):
        failure = work / ("build/" + mode + "-failure")
        result = capture("execute-failure-" + mode, [python, helper, "--execute", work / "build/query"],
                         env | {"GI_TEST_MODE": mode, "GI_TEST_PHASES": str(work / ("execute-" + mode + "-phases")),
                                "EMBERBSD_GI_FAILURE_MARKER": str(failure)})
        require(result.returncode != 0 and failure.is_file(), "unrecorded execute infrastructure failure: " + mode + ": " + result.stdout)
    require(all(digest(path) == expected for path, expected in inputs.items()), "production inputs changed during the test")
    (work / "result.json").write_text(json.dumps({"status": "PASS", "target": args.target,
        "scope": "Real cross-linked ELF, both target make metadata sets, production shell guards and mocked SSH transport. No VM or target executable execution.",
        "inputs": inputs, "commands": commands}, indent=2) + "\n")
    print("PASS: all refusals, transport failures, installed-provider reuse, publication, separate streams/status and failure markers")


if __name__ == "__main__":
    main()
