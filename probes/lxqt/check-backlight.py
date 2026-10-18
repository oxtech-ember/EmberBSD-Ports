#!/usr/bin/env python3
"""Check the actual liblxqt backlight helper with private synthetic devices."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="original or patched liblxqt 2.4.0")
    parser.add_argument("output", type=Path)
    parser.add_argument("--cc", default="cc", help="native compiler with ASan/UBSan")
    parser.add_argument("--baseline", action="store_true", help="expect the original defects")
    args = parser.parse_args()
    source = args.source.resolve() / "lxqtbacklight/linux_backend/driver"
    output = args.output.absolute()
    if output.exists():
        parser.error("output directory already exists")
    output.mkdir(parents=True)
    (output / "tmp").mkdir()
    (output / "empty").mkdir()
    for directory, kinds in (("single", ["raw"]),
                             ("multiple", ["platform"] * 2 + ["raw"] * 2 + ["other"] * 2)):
        for index, kind in enumerate(kinds):
            device = output / directory / ("device" + str(index))
            device.mkdir(parents=True)
            for name, value in (("type", kind), ("max_brightness", "100"),
                                ("actual_brightness", "40"), ("bl_power", "0"),
                                ("brightness", "1")):
                (device / name).write_text(value + "\n")
    environment = dict(os.environ, TMPDIR=str(output / "tmp"),
                       ASAN_OPTIONS="halt_on_error=1",
                       UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    binary = output / "backlight-test"
    command = [args.cc, "-O1", "-g", "-fsanitize=address,undefined",
               "-fno-omit-frame-pointer", "-ftrivial-auto-var-init=pattern",
               "-I" + str(source), str(Path(__file__).with_name("tests") / "backlight-no-device.c"),
               "-o", str(binary)]
    with (output / "compile.log").open("w") as log:
        subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
    results = []

    def run(name, directory, data, expected, extra=()):
        result = subprocess.run([str(binary), str(output / directory), *extra],
                                input=data, text=True, capture_output=True,
                                env=environment, timeout=30)
        (output / (name + ".log")).write_text(result.stdout + result.stderr)
        results.append({"case": name, "status": result.returncode,
                        "stdout": result.stdout, "expected_status": expected})
        if result.returncode != expected or "runtime error:" in result.stderr or "AddressSanitizer" in result.stderr:
            raise RuntimeError("unexpected helper result: " + name)
        return result.stdout

    run("no-device", "empty", "", 42 if args.baseline else 0)
    run("replaced-drivers", "multiple", "50\n", 43 if args.baseline else 0)
    text = run("malformed-stdin", "single", "50\nbad\n", 0)
    if text != "writes=" + ("2" if args.baseline else "1") + "\n":
        raise RuntimeError("malformed input caused an unexpected write count")
    maximum = output / "single/device0/max_brightness"
    maximum.write_text("bad\n")
    run("malformed-device-value", "single", "", 44 if args.baseline else 0, ("device0",))
    maximum.write_text("100\n")
    for value in (50, 100, 0, 101):
        brightness = output / "single/device0/brightness"
        brightness.write_text("1\n")
        run("level-" + str(value), "single", str(value) + "\n", 0)
        if int(brightness.read_text()) != (value if 0 < value <= 100 else 1):
            raise RuntimeError("brightness control changed: " + str(value))
    receipt = {"compile_command": command, "baseline": args.baseline, "cases": results,
               "source_sha256": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                                 for name in ("lxqtbacklight_backend.c", "libbacklight_backend.c")},
               "scope": "Native ASan/UBSan and real-source contract/ownership controls; no hardware"}
    (output / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("PASS: expected helper contracts and all valid brightness boundaries")


if __name__ == "__main__":
    main()
