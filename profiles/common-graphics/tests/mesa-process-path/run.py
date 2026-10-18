#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual-source host contract and target probes.
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile


def digest(path, algorithm="sha256"):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def main():
    if len(sys.argv) != 5:
        raise SystemExit("Usage: run.py MESA_ARCHIVE SYSROOT CROSS_CC NEW_WORK")
    archive, sysroot, cross_cc = (Path(arg).resolve(strict=True) for arg in sys.argv[1:4])
    work = Path(sys.argv[4])
    if not work.is_absolute() or work.exists() or work.is_symlink():
        raise SystemExit("Use a new absolute work directory")
    work.mkdir(parents=True)
    here = Path(__file__).resolve().parent
    recipe = here.parent.parent / "recipes/graphics/MesaLib"
    commands = []

    def run(label, argv, expected=0, cwd=None):
        args = [str(arg) for arg in argv]
        result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
        (work / (label + ".stdout")).write_text(result.stdout)
        (work / (label + ".stderr")).write_text(result.stderr)
        commands.append({"label": label, "argv": args, "cwd": str(cwd) if cwd else None,
                         "status": result.returncode, "expected_status": expected})
        (work / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if result.returncode != expected:
            raise AssertionError(f"{label}: status {result.returncode}: {result.stderr}")
        return result.stdout

    expected = re.search(r"^SHA512 \(" + re.escape(archive.name) + r"\) = ([0-9a-f]{128})$",
                         (recipe / "distinfo").read_text(), re.MULTILINE)
    if expected is None or digest(archive, "sha512") != expected[1]:
        raise AssertionError("Pinned Mesa archive differs")
    patch = recipe / "patches/patch-src_util_u__process.c"
    filtered = b"".join(line for line in patch.read_bytes().splitlines(keepends=True)
                        if b"$NetBSD" not in line)
    patch_hash = hashlib.sha1(filtered).hexdigest()
    if f"SHA1 ({patch.name}) = {patch_hash}\n" not in (recipe / "distinfo").read_text():
        raise AssertionError("pkgsrc RCS-filtered patch checksum differs")
    tree = work / "source"
    with tarfile.open(archive, "r:xz") as bundle:
        for name in ("src/util/u_process.c", "src/util/detect_os.h"):
            path = tree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bundle.extractfile("mesa-26.2.4/" + name).read())
    source = tree / "src/util/u_process.c"
    before = source.read_text()
    run("apply-production-patch", ["patch", "--batch", "--fuzz=0", "-p0", "-i", patch], cwd=tree)
    after = source.read_text()

    def function(text):
        start = text.index("size_t\nutil_get_process_exec_path(")
        end = text.index("\nbool\nutil_get_command_line(", start)
        return text[start:end]

    host_cc = shutil.which(os.environ.get("CC", "cc"))
    if host_cc is None:
        raise AssertionError("Real native GCC16 is required through CC")
    for label, cc in (("host", host_cc), ("target", cross_cc)):
        if not run(label + "-gcc-version", [cc, "-dumpfullversion"]).strip().startswith("16."):
            raise AssertionError("GCC16 is required")
    if "netbsd" not in run("target-machine", [cross_cc, "-dumpmachine"]).lower():
        raise AssertionError("A NetBSD target compiler is required")
    headers = (sysroot / "usr/include/sys/sysctl.h").read_text()
    constants = []
    for name in ("CTL_KERN", "KERN_PROC_ARGS", "KERN_PROC_PATHNAME"):
        match = re.search(r"^#define\s+" + name + r"\s+([0-9]+)\b", headers, re.MULTILINE)
        if match is None:
            raise AssertionError("Missing target sysctl constant: " + name)
        constants.append(f"#define {name} {match[1]}\n")
    (work / "sysctl-values.h").write_text("".join(constants))
    common = "#include <sys/types.h>\n#include <unistd.h>\n#include <string.h>\n#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))\n"
    target_prefix = common + '#include <sys/sysctl.h>\n#include "detect_os.h"\n'
    host_prefix = common + '''#include "sysctl-values.h"
#define DETECT_OS_NETBSD 1
#define DETECT_OS_POSIX 1
int contract_sysctl(const int *, unsigned int, void *, size_t *, const void *, size_t);
ssize_t contract_readlink(const char *, char *, size_t);
#define sysctl contract_sysctl
#define readlink contract_readlink
'''
    flags = ["-std=c11", "-Wall", "-Werror", "-O1", "-g"]
    outputs = {}
    for role, prefix in (("target", target_prefix), ("host", host_prefix)):
        for version, text in (("before", before), ("after", after)):
            path = work / f"{role}-{version}.c"
            path.write_text(prefix + function(text))
            output = work / f"{role}-{version}"
            if role == "target":
                argv = [cross_cc, "--sysroot=" + str(sysroot), "-D_NETBSD_SOURCE",
                        "-I" + str(tree / "src/util"), *flags, path, here / "target.c", "-o", output]
            else:
                argv = [host_cc, "-D_POSIX_C_SOURCE=200809L", "-I" + str(work),
                        *flags, path, here / "contract.c", "-o", output]
            run("build-" + role + "-" + version, argv)
            outputs[role + "-" + version] = {"path": str(output), "sha256": digest(output)}
    run("host-before-red", [work / "host-before"], expected=1)
    if "path works without procfs" not in (work / "host-before-red.stderr").read_text():
        raise AssertionError("Baseline did not fail at the causal path assertion")
    run("host-after-green", [work / "host-after"])
    receipt = {"status": "PASS", "scope": "Exact upstream/patched function, explicit host syscall-boundary contract and genuine GCC16 NetBSD probe builds. Target execution is required separately.",
               "archive_sha512": expected[1], "patch_sha1_rcs_filtered": patch_hash,
               "upstream_source_sha256": hashlib.sha256(before.encode()).hexdigest(),
               "patched_source_sha256": digest(source), "outputs": outputs,
               "target_cli": "target-before --require-no-proc (expect failure); target-after --require-no-proc (expect success)",
               "target_execution": "PENDING"}
    (work / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("PASS: causal host RED/GREEN; genuine GCC16 target probes built, execution pending")
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
