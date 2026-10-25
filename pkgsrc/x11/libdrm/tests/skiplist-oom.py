#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: AI-assisted EmberBSD; compile and execute actual skip-list allocation paths.
"""Run the libdrm skip-list allocation regression on an explicit GCC16 target."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


FIXTURE = Path(__file__).with_name("skiplist-oom.c")
EXPECTED_OUTPUT = [
    "PASS: list allocation failure",
    "PASS: head allocation failure cleanup",
    "PASS: insertion random-state failure",
    "PASS: insertion node allocation failure",
    "PASS: insertion recovery, duplicate semantics, and destruction",
]


def require(condition, message):
    if not condition:
        raise SystemExit("FAIL: " + message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(label, command, cwd, output_dir, expected_status):
    command = list(map(str, command))
    record_path = output_dir / (label + ".command.json")
    record_path.write_text(json.dumps({
        "argv": command,
        "cwd": str(cwd),
        "expected_exit": expected_status,
    }, indent=2) + "\n", encoding="utf-8")
    result = subprocess.run(command, cwd=cwd, capture_output=True, check=False)
    (output_dir / (label + ".stdout")).write_bytes(result.stdout)
    (output_dir / (label + ".stderr")).write_bytes(result.stderr)
    require(result.returncode == expected_status,
            f"{label}: exit {result.returncode}, expected {expected_status}; "
            + result.stderr.decode(errors="replace"))
    return result


def validate_runner(runner_argv):
    if not runner_argv:
        return
    executable = Path(runner_argv[0])
    require(executable.is_absolute(),
            "the first --runner-arg must be an absolute executable path")
    require(executable.is_file() and os.access(executable, os.X_OK),
            "the first --runner-arg must name an executable file")


def normalize_arch(value):
    value = value.lower()
    return {"amd64": "x86_64", "arm64": "aarch64"}.get(value, value)


def validate_native_execution(machine, runner_argv):
    if runner_argv:
        return
    target_arch = machine.split("-", 1)[0]
    require(sys.platform.startswith("netbsd"),
            "a --runner-arg is required when the host is not NetBSD")
    require(normalize_arch(platform.machine()) == normalize_arch(target_arch),
            "a --runner-arg is required when host and GCC target architectures differ")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path,
                        help="absolute path to the patched xf86drmSL.c")
    parser.add_argument("--compiler", required=True, type=Path,
                        help="absolute path to GCC 16 targeting NetBSD")
    parser.add_argument("--config-header", required=True, type=Path,
                        help="absolute path to this package build's generated config.h")
    parser.add_argument("--include-dir", action="append", type=Path, default=[],
                        help="include directory; repeat for each required package source directory")
    parser.add_argument("--output", required=True, type=Path,
                        help="new absolute directory for the binary and command results")
    parser.add_argument("--runner-arg", action="append", default=[], metavar="ARG",
                        help="append one target-runner argv token; repeat for options; binary path is appended")
    args = parser.parse_args()

    for name in ("source", "compiler", "config_header", "output"):
        path = getattr(args, name)
        require(path.is_absolute(), f"--{name.replace('_', '-')} must be absolute")
    require(args.source.is_file(), "--source must name a regular file")
    require(args.source.name == "xf86drmSL.c" or
            args.source.name.endswith("xf86drmSL.fixed.c"),
            "--source must name the patched xf86drmSL.c source")
    require(args.compiler.is_file() and os.access(args.compiler, os.X_OK),
            "--compiler must name an executable GCC16 driver")
    require(args.config_header.is_file(), "--config-header must name a regular file")
    require(not args.output.exists(), "--output directory already exists")
    require(args.output.parent.is_dir(), "--output parent directory must already exist")
    validate_runner(args.runner_arg)

    source = args.source.resolve()
    compiler = args.compiler.resolve()
    config_header = args.config_header.resolve()
    include_dirs = [path.resolve() for path in args.include_dir]
    if not include_dirs:
        include_dirs = [source.parent, source.parent / "include" / "drm"]
    for include_dir in include_dirs:
        require(include_dir.is_dir(), f"include directory does not exist: {include_dir}")

    args.output.mkdir()
    output_dir = args.output.resolve()
    binary = output_dir / "skiplist-oom"

    banner = record("compiler-banner", [compiler, "--version"],
                    source.parent, output_dir, 0).stdout.decode(errors="replace")
    version = record("compiler-version", [compiler, "-dumpfullversion"],
                     source.parent, output_dir, 0).stdout.decode().strip()
    machine = record("compiler-machine", [compiler, "-dumpmachine"],
                     source.parent, output_dir, 0).stdout.decode().strip()
    require(version.startswith("16.") and "gcc" in banner.lower() and
            "clang" not in banner.lower(),
            "the selected compiler must be GCC 16")
    require("netbsd" in machine.lower(),
            "GCC16 must target NetBSD")
    validate_native_execution(machine, args.runner_arg)

    compile_argv = [
        str(compiler), "-std=c11", "-Wall", "-Werror",
        "-Wstrict-prototypes", "-Wmissing-prototypes",
        "-Wmissing-declarations", "-Werror=implicit-function-declaration",
        "-Wpointer-arith", "-Wwrite-strings", "-Wshadow",
        "-Wold-style-definition", "-include", str(config_header),
    ]
    for include_dir in include_dirs:
        compile_argv.extend(("-I", str(include_dir)))
    compile_argv.extend(("-o", str(binary), str(source), str(FIXTURE.resolve())))
    record("compile", compile_argv, source.parent, output_dir, 0)

    runtime_argv = [*args.runner_arg, str(binary)]
    run = record("runtime", runtime_argv, output_dir, output_dir, 0)
    output = run.stdout.decode("ascii", errors="replace").splitlines()
    require(output == EXPECTED_OUTPUT,
            "runtime allocation, recovery, duplicate, or cleanup results differ")

    result = {
        "source": str(source),
        "source_sha256": sha256(source),
        "fixture": str(FIXTURE.resolve()),
        "fixture_sha256": sha256(FIXTURE),
        "config_header": str(config_header),
        "config_header_sha256": sha256(config_header),
        "compiler": str(compiler),
        "compiler_banner": banner.strip(),
        "compiler_version": version,
        "compiler_machine": machine,
        "include_dirs": list(map(str, include_dirs)),
        "compile_argv": compile_argv,
        "runner_argv": args.runner_arg,
        "runtime_argv": runtime_argv,
        "runtime_exit": run.returncode,
        "runtime_stdout": output,
    }
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS: skip-list allocation failure, recovery, and cleanup regression")
    print(f"RESULT: {output_dir / 'result.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
