#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; causal source regressions for GCC16 ctype and OOM paths.
"""Apply the libdrm patch and execute its actual ASIC-ID parser functions."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile


PACKAGE = Path(__file__).resolve().parents[1]
MEMBER = "libdrm-2.4.134/amdgpu/amdgpu_asic_id.c"
PATCH_NAME = "patch-zzzzz-amdgpu-ctype"
FIXTURE = Path(__file__).with_name("amdgpu-asic-id-ctype.c")
OOM_FIXTURE = Path(__file__).with_name("amdgpu-asic-id-oom.c")


def require(condition, message):
    if not condition:
        raise SystemExit("FAIL: " + message)


def sha1_patch(path):
    raw = path.read_bytes()
    filtered = b"".join(
        line for line in raw.splitlines(keepends=True) if b"$NetBSD" not in line
    )
    return hashlib.sha1(filtered).hexdigest()


def record(name, command, cwd, work, expected_status):
    command = list(map(str, command))
    (work / (name + ".command.json")).write_text(
        json.dumps({"argv": command, "cwd": str(cwd),
                    "expected_exit": expected_status}, indent=2) + "\n",
        encoding="utf-8")
    result = subprocess.run(command, cwd=cwd, capture_output=True, check=False)
    (work / (name + ".stdout")).write_bytes(result.stdout)
    (work / (name + ".stderr")).write_bytes(result.stderr)
    require(result.returncode == expected_status,
            f"{name}: exit {result.returncode}, expected {expected_status}; "
            + result.stderr.decode(errors="replace"))
    return result


def parser_function(source):
    text = source.read_text(encoding="utf-8")
    start = text.find("static int parse_one_line(")
    end = text.find("\nstatic void amdgpu_parse_proc_cpuinfo", start)
    require(start >= 0 and end > start,
            "upstream parser function boundaries changed; update the source check")
    return text[start:end] + "\n"


def source_function(source, signature):
    text = source.read_text(encoding="utf-8")
    start = text.find(signature)
    end = text.find("\n}", start)
    require(start >= 0 and end > start,
            f"upstream function boundary changed: {signature}")
    return text[start:end + 2] + "\n"


def validate_runner(runner_argv):
    if not runner_argv:
        return
    executable = Path(runner_argv[0])
    require(
        executable.is_absolute(),
        "the first --runner-arg must be an absolute executable path",
    )
    require(executable.is_file() and os.access(executable, os.X_OK),
            "the first --runner-arg must name an executable file")


def runtime_command(binary, runner_argv):
    return [*runner_argv, str(binary)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--cc", required=True, type=Path)
    parser.add_argument("--patch-tool", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument(
        "--runner-arg", action="append", default=[], metavar="ARG",
        help="append one target-runner argv token; repeat for runner options; the test binary is appended",
    )
    args = parser.parse_args()

    for name in ("archive", "cc", "patch_tool"):
        path = getattr(args, name)
        require(path.is_absolute(), f"--{name.replace('_', '-')} must be absolute")
        require(path.is_file(), f"--{name.replace('_', '-')} must be a regular file")
    require(os.access(args.cc, os.X_OK), "--cc must be executable")
    require(os.access(args.patch_tool, os.X_OK), "--patch-tool must be executable")
    validate_runner(args.runner_arg)
    require(args.work.is_absolute(), "--work must be an absolute path")
    require(not args.work.exists(), "--work already exists")
    args.work.mkdir(parents=True)

    patch = PACKAGE / "patches" / PATCH_NAME
    distinfo = (PACKAGE / "distinfo").read_text(encoding="ascii")
    patch_digest = sha1_patch(patch)
    require(f"SHA1 ({PATCH_NAME}) = {patch_digest}" in distinfo,
            "distinfo does not contain the canonical patch checksum")

    archive_bytes = args.archive.read_bytes()
    archive_hashes = {
        "BLAKE2s": hashlib.blake2s(archive_bytes).hexdigest(),
        "SHA512": hashlib.sha512(archive_bytes).hexdigest(),
    }
    for algorithm, digest in archive_hashes.items():
        require(f"{algorithm} ({args.archive.name}) = {digest}" in distinfo,
                f"distinfo {algorithm} mismatch")
    require(f"Size ({args.archive.name}) = {len(archive_bytes)} bytes" in distinfo,
            "distinfo archive size mismatch")

    banner = record("compiler-banner", [args.cc, "--version"], PACKAGE,
                    args.work, 0).stdout.decode(errors="replace")
    version = record("compiler-version", [args.cc, "-dumpfullversion"], PACKAGE,
                     args.work, 0).stdout.decode().strip()
    machine = record("compiler-machine", [args.cc, "-dumpmachine"], PACKAGE,
                     args.work, 0).stdout.decode().strip()
    require(version.startswith("16.") and "clang" not in banner.lower(),
            "an absolute GCC16 driver is required")
    require(
        "netbsd" in machine.lower(),
        "GCC16 must target NetBSD so both controls use NetBSD ctype headers",
    )

    source_root = args.work / "source"
    upstream_root = source_root / "upstream"
    candidate_root = source_root / "patched"
    upstream_dir = upstream_root / "amdgpu"
    candidate_dir = candidate_root / "amdgpu"
    upstream_dir.mkdir(parents=True)
    candidate_dir.mkdir(parents=True)
    with tarfile.open(args.archive, "r:xz") as archive:
        member = archive.getmember(MEMBER)
        require(member.isfile(), "pinned archive member is not a regular file")
        extracted = archive.extractfile(member)
        require(extracted is not None, "cannot read pinned archive member")
        upstream_source = upstream_dir / "amdgpu_asic_id.c"
        upstream_source.write_bytes(extracted.read())

    candidate_source = candidate_dir / "amdgpu_asic_id.c"
    shutil.copyfile(upstream_source, candidate_source)
    upstream_hash = hashlib.sha256(upstream_source.read_bytes()).hexdigest()
    (args.work / "upstream-source.sha256").write_text(
        upstream_hash + "  " + MEMBER + "\n", encoding="ascii")
    record("apply-patch", [args.patch_tool, "-p0", "-F0", "-i", patch],
           candidate_root, args.work, 0)
    candidate_hash = hashlib.sha256(candidate_source.read_bytes()).hexdigest()
    (args.work / "candidate-source.sha256").write_text(
        candidate_hash + "  " + MEMBER + "\n", encoding="ascii")

    fixture = FIXTURE.read_text(encoding="utf-8")
    oom_fixture = OOM_FIXTURE.read_text(encoding="utf-8")
    compile_flags = [
        args.cc, "-std=c11", "-Wall", "-Wextra", "-Werror",
        "-Werror=char-subscripts", "-o",
    ]
    runtime_invocations = []
    for label, tree, expected in (("upstream", upstream_root, 1),
                                  ("patched", candidate_root, 0)):
        function = parser_function(tree / "amdgpu/amdgpu_asic_id.c")
        case_dir = args.work / label
        case_dir.mkdir()
        (case_dir / "parse_one_line.inc").write_text(function, encoding="utf-8")
        harness_path = case_dir / "fixture.c"
        harness_path.write_text(fixture, encoding="utf-8")
        binary = case_dir / "fixture"
        result = record(label + "-compile", compile_flags + [binary,
            harness_path], case_dir, args.work, expected)
        if label == "upstream":
            require(b"char-subscripts" in result.stderr,
                    "upstream cause control failed for a reason other than char-subscripts")
            continue
        runtime_argv = runtime_command(binary, args.runner_arg)
        run = record("patched-runtime", runtime_argv, case_dir, args.work, 0)
        runtime_invocations.append(runtime_argv)
        outputs = run.stdout.decode("ascii").splitlines()
        require(outputs == [
            "PASS: trim-space-and-tab",
            "PASS: preserve-high-bit-name-byte",
            "PASS: preserve-vertical-tab",
            "PASS: reject-space-and-tab-only-name",
        ], "patched parser runtime cases differ")

    oom_compile_flags = [
        args.cc, "-std=c11", "-Wall", "-Wextra", "-Werror",
        "-Werror=char-subscripts", "-o",
    ]
    oom_results = []
    for label, tree in (("upstream", upstream_root),
                        ("patched", candidate_root)):
        source_path = tree / "amdgpu/amdgpu_asic_id.c"
        oom_dir = args.work / (label + "-oom")
        oom_dir.mkdir()
        (oom_dir / "amdgpu_parse_asic_ids.inc").write_text(
            source_function(source_path, "void amdgpu_parse_asic_ids("),
            encoding="utf-8")
        harness_path = oom_dir / "fixture.c"
        harness_path.write_text(oom_fixture, encoding="utf-8")
        binary = oom_dir / "fixture"
        record(label + "-oom-compile",
               oom_compile_flags + [binary, harness_path], oom_dir,
               args.work, 0)
        runtime_argv = runtime_command(binary, args.runner_arg)
        expected_status = 1 if label == "upstream" else 0
        run = record(label + "-oom-runtime", runtime_argv, oom_dir,
                     args.work, expected_status)
        runtime_invocations.append(runtime_argv)
        if label == "upstream":
            require(b"fopen received the failed path" in run.stderr,
                    "upstream OOM control did not reach fopen with NULL")
            continue
        outputs = run.stdout.decode("ascii").splitlines()
        require(outputs == [
            "PASS: oom-preserves-fusion-cpu-fallback",
            "PASS: oom-skips-non-fusion-cpu-fallback",
        ], "patched OOM fallback cases differ")
        oom_results = outputs

    manifest = {
        "status": "PASS",
        "libdrm_version": "2.4.134",
        "archive": str(args.archive),
        "archive_size": len(archive_bytes),
        "archive_hashes": archive_hashes,
        "patch": PATCH_NAME,
        "patch_sha1_pkgsrc": patch_digest,
        "upstream_source_sha256": upstream_hash,
        "candidate_source_sha256": candidate_hash,
        "compiler": str(args.cc),
        "compiler_version": version,
        "compiler_machine": machine,
        "runner_argv": args.runner_arg,
        "runtime_invocations": runtime_invocations,
        "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        "oom_fixture_sha256": hashlib.sha256(OOM_FIXTURE.read_bytes()).hexdigest(),
        "parser_cases": 4,
        "oom_failure_cases": len(oom_results),
        "scope": "Actual parse_one_line and amdgpu_parse_asic_ids functions extracted from the pinned upstream source. GCC16 compile controls target NetBSD; runtime is native unless a target runner is supplied. OOM cases force strdup failure and check no NULL path reaches fopen or %s, cleanup, and the fusion CPU-info fallback. No DRM device access or GPU execution.",
    }
    (args.work / "result.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: four parser and two allocation-failure cases; receipt {args.work / 'result.json'}")


if __name__ == "__main__":
    main()
