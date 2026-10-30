#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real-input preparation refusal regressions.
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    if len(sys.argv) != 8:
        raise SystemExit("usage: epoxy-bundle.test.py CROSS_TOOLS SYSROOT EPOXY_BUILD EPOXY_PACKAGE MESA_BUNDLE CONSUMER_WORK NEW_WORK")
    tools, sysroot, original_build, package, original_mesa, consumer = (Path(arg).resolve(strict=True) for arg in sys.argv[1:7])
    work = Path(sys.argv[7])
    if not work.is_absolute() or work.exists() or work.is_symlink():
        raise SystemExit("NEW_WORK must be new and absolute")
    work.mkdir(parents=True)
    helper = Path(__file__).resolve().parent.parent / "cross/prepare-epoxy-tests.py"
    build = work / "actual-build-copy"
    (build / "meson-info").mkdir(parents=True)
    (build / "test").mkdir()
    (build / "src").mkdir()
    shutil.copy2(original_build / "meson-info/intro-projectinfo.json", build / "meson-info")
    tests = json.loads((original_build / "meson-info/intro-tests.json").read_text())
    selected = {"header_guards", "misc_defines", "khronos_typedefs", "gl_version"}
    tests = [test for test in tests if test["name"] in selected]
    for test in tests:
        executable = build / "test" / Path(test["cmd"][0]).name
        shutil.copy2(test["cmd"][0], executable)
        test["cmd"] = [str(executable)]
        test["env"] = {"LD_LIBRARY_PATH": str(build / "src")}
    metadata = build / "meson-info/intro-tests.json"
    metadata.write_text(json.dumps(tests, indent=2) + "\n")
    outcomes = []

    def check(name, expected=None, mesa=original_mesa):
        command = [sys.executable, str(helper), str(tools), str(sysroot), str(build), str(package),
                   str(mesa), str(consumer), str(work / name)]
        result = subprocess.run(command, text=True, capture_output=True, timeout=300, check=False)
        output = result.stdout + result.stderr
        (work / (name + ".log")).write_text(output)
        valid = result.returncode == 0 if expected is None else result.returncode != 0 and expected in output
        outcomes.append({"name": name, "argv": command, "status": result.returncode, "expected": expected, "pass": valid})
        (work / "commands.json").write_text(json.dumps(outcomes, indent=2) + "\n")
        if not valid:
            raise SystemExit("FAIL: " + name)
        print("PASS: " + name, flush=True)

    # Genuine test executable copies and relocated Meson metadata establish the control.
    check("actual-inputs")
    changed_mesa = work / "mesa-identity-fixture"
    shutil.copytree(original_mesa, changed_mesa, symlinks=True)
    manifest = changed_mesa / "artifacts.sha256"
    contents = next(changed_mesa / name for name in ("source/MesaLib.CONTENTS", "MesaLib.CONTENTS")
                    if (changed_mesa / name).is_file())
    original_contents, original_manifest = contents.read_text(), manifest.read_text()
    relative = str(contents.relative_to(changed_mesa))
    for name, replacement in (("wrong-mesa-identity", original_contents.replace("@name MesaLib-26.2.6nb10\n", "@name MesaLib-26.2.4nb3\n")),
                              ("duplicate-mesa-identity", original_contents + "@name MesaLib-26.2.6nb10\n")):
        if replacement == original_contents:
            raise SystemExit("current genuine Mesa identity was not exercised")
        contents.write_text(replacement)
        checksum = hashlib.sha256(contents.read_bytes()).hexdigest()
        # Rehash only the explicit parser fixture so the identity guard causes the refusal.
        manifest.write_text("".join((checksum + "  " + relative if line.split("  ", 1)[1] == relative else line) + "\n"
                                    for line in original_manifest.splitlines()))
        check(name, "require the accepted Mesa package: MesaLib-26.2.6nb10", changed_mesa)
    shutil.rmtree(changed_mesa)
    for name, value in (("zero-timeout", 0), ("boolean-timeout", True), ("oversized-timeout", 121)):
        changed = copy.deepcopy(tests)
        changed[0]["timeout"] = value
        metadata.write_text(json.dumps(changed) + "\n")
        check(name, "unbounded upstream test")
    for name, changed in (("missing-test", tests[1:]), ("duplicate-test", tests + [tests[0]])):
        metadata.write_text(json.dumps(changed) + "\n")
        check(name, "missing/duplicate upstream tests")
    changed = copy.deepcopy(tests)
    changed[0]["env"]["LD_PRELOAD"] = "/foreign/lib.so"
    metadata.write_text(json.dumps(changed) + "\n")
    check("extra-environment", "unexpected pure test prerequisites")
    changed = copy.deepcopy(tests)
    changed[0]["cmd"].append("unexpected argument")
    metadata.write_text(json.dumps(changed) + "\n")
    check("extra-argument", "unexpected pure test prerequisites")
    metadata.write_text(json.dumps(tests) + "\n")
    executable = Path(tests[0]["cmd"][0])
    data = executable.read_bytes()
    executable.write_bytes(data[:18] + b"\x3e\x00" + data[20:])
    check("wrong-elf-machine", "not AArch64 ELF")
    executable.write_bytes(data)
    print("PASS: genuine-input control and ten causal preparation refusals; no target code executed")


if __name__ == "__main__":
    main()
