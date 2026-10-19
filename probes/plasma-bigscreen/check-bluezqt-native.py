#!/usr/bin/env python3
"""Build BluezQt's real client and upstream tests on an isolated Darwin bus.

This is a native memory regression, not an EmberBSD package build or a
Bluetooth hardware test. Select the work storage explicitly before running.
"""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["archive", "work", "qt-prefix", "ecm", "cc", "cxx",
                 "cmake", "ninja", "ctest", "dbus-run-session"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error("this runner requires Darwin; it does not isolate Linux rfkill devices")
    if not all(value.is_absolute() for value in vars(args).values()):
        parser.error("all input and output paths must be absolute")
    if args.work.exists():
        parser.error("select a new work directory")
    expected = "22b25448c6b5372ee4fba15bb938e698a599cec0d69816ceb0405451c879c827"
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != expected:
        parser.error("BluezQt 6.31.0 archive checksum differs")
    # Qt's public version file includes this generated implementation.
    qt_version = args.qt_prefix / "lib/cmake/Qt6Core/Qt6CoreConfigVersionImpl.cmake"
    if not qt_version.is_file() or not re.search(
            r'set\(PACKAGE_VERSION "6\.12\.0"\)', qt_version.read_text()):
        parser.error("select the matching native Qt 6.12.0 prefix")
    args.work.mkdir(parents=True)
    temporary = args.work / "tmp"
    temporary.mkdir()
    env = dict(os.environ, TMPDIR=str(temporary), PYTHONDONTWRITEBYTECODE="1")
    env.pop("KF_IGNORE_PLATFORM_CHECK", None)
    records = {"scope": "native Darwin client only; no target or Bluetooth acceptance",
               "archive_sha256": expected, "steps": []}

    def save():
        (args.work / "result.json").write_text(json.dumps(records, indent=2) + "\n")

    def run(label, command, cwd=None, environment=None):
        command = [str(item) for item in command]
        record = {"label": label, "command": command}
        records["steps"].append(record)
        save()
        with (args.work / (label + ".log")).open("w") as log:
            try:
                result = subprocess.run(command, cwd=cwd, env=environment or env,
                                        stdout=log, stderr=subprocess.STDOUT)
            except KeyboardInterrupt:
                record["status"] = 130
                save()
                raise
        record["status"] = result.returncode
        save()
        if result.returncode:
            raise SystemExit(f"{label} failed; inspect its log in {args.work}")

    with tarfile.open(args.archive) as archive:
        archive.extractall(args.work, filter="data")
    source = args.work / "bluez-qt-6.31.0"
    patches = Path(__file__).resolve().parent / "recipes/comms/kf6-bluez-qt/patches"
    for patch in sorted(patches.iterdir()):
        run(patch.name, ["patch", "-f", "-F", "0", "-p0", "-i", patch], cwd=source)
    objects = args.work / "objects"
    sanitizer = "-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer"
    run("configure", [args.cmake, "-S", source, "-B", objects, "-G", "Ninja",
        "-DCMAKE_MAKE_PROGRAM=" + str(args.ninja),
        "-DCMAKE_PREFIX_PATH=" + str(args.qt_prefix), "-DECM_DIR=" + str(args.ecm),
        "-DQt6_DIR=" + str(args.qt_prefix / "lib/cmake/Qt6"),
        "-DCMAKE_C_COMPILER=" + str(args.cc), "-DCMAKE_CXX_COMPILER=" + str(args.cxx),
        "-DCMAKE_C_FLAGS=" + sanitizer, "-DCMAKE_CXX_FLAGS=" + sanitizer,
        "-DCMAKE_BUILD_TYPE=Debug", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        "-DCMAKE_INSTALL_PREFIX=" + str(args.work / "stage"),
        "-DBUILD_TESTING=ON", "-DKF_IGNORE_PLATFORM_CHECK=OFF"])
    systems = list((objects / "CMakeFiles").glob("*/CMakeSystem.cmake"))
    if len(systems) != 1 or 'set(CMAKE_CROSSCOMPILING "FALSE")' not in systems[0].read_text():
        raise SystemExit("the configured compiler is not a native toolchain")
    run("build", [args.cmake, "--build", objects, "--parallel", "1"])
    testing = dict(env, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=" + str(temporary / "no-system-bus"),
        ASAN_OPTIONS="detect_leaks=0:abort_on_error=1",
        UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    run("tests", [args.dbus_run_session, "--", args.ctest, "--test-dir", objects,
        "--output-on-failure", "--parallel", "1", "--output-junit", args.work / "tests.xml"],
        environment=testing)
    cases = ET.parse(args.work / "tests.xml").getroot().findall(".//testcase")
    if not cases or any(case.find("skipped") is not None or case.find("failure") is not None
                        or case.find("error") is not None for case in cases):
        raise SystemExit("the upstream test run is empty, skipped or unsuccessful")
    if not any("qmltests" in case.get("name", "") for case in cases):
        raise SystemExit("the upstream QML test did not execute")
    records["ctest_invocations"] = len(cases)
    records["memory_boundary"] = (
        "ASan/UBSan instrument this source. External Qt libraries are not instrumented. "
        "Darwin arm64 has no supported Memcheck/LeakSanitizer run in this check.")
    records["status"] = "PASS"
    save()
    print(f"PASS: {len(cases)} upstream native client test invocations; no target acceptance")


if __name__ == "__main__":
    main()
