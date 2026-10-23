#!/usr/bin/env python3
# Origin: EmberBSD, AI-assisted by OpenAI Codex (GPT-6).
"""Build a checked Linux AArch64 diagnostic, not an EmberBSD package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
PORTS = HERE.parents[1]
URL = "https://pyropus.ca./software/memtester/old-versions/memtester-4.7.1.tar.gz"
SHA256 = "e427de663f7bd22d1ebee8af12506a852c010bd4fcbca1e0e6b02972d298b5bb"
IMAGE = "gcc@sha256:b89e1771f0ac16e3769dd351ea8e07a6676aa690a76339c16e36c761eaaaf0f9"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    work, output = args.work.resolve(), args.output.resolve()
    work.mkdir(parents=True, exist_ok=False)
    output.mkdir(parents=True, exist_ok=False)
    logs = output / "logs"
    logs.mkdir()
    record = {"status": "started", "commands": [], "scope": __doc__,
              "ports_commit": os.environ["GITHUB_SHA"],
              "run_url": "https://github.com/" + os.environ["GITHUB_REPOSITORY"] +
                         "/actions/runs/" + os.environ["GITHUB_RUN_ID"],
              "image": os.environ["GCC_IMAGE"], "host": platform.uname()._asdict()}

    def run(command, name):
        command = [str(x) for x in command]
        result = subprocess.run(command, capture_output=True)
        (logs / (name + ".log")).write_bytes(result.stdout + result.stderr)
        record["commands"].append({"argv": command, "status": result.returncode})
        if result.returncode:
            print((result.stdout + result.stderr).decode(errors="replace"), flush=True)
            raise RuntimeError(f"{name}: exit {result.returncode}")
        return result.stdout.decode()

    try:
        if platform.system() != "Linux" or platform.machine() != "aarch64":
            raise RuntimeError("native Linux AArch64 is required")
        if record["image"] != IMAGE:
            raise RuntimeError("unexpected compiler image")
        if run(["gcc", "-dumpfullversion"], "gcc-version").strip() != "16.2.0":
            raise RuntimeError("GCC 16.2.0 is required")
        record["tool_versions"] = {
            name: run([name, "--version"], name + "-version-full").splitlines()[0]
            for name in ("gcc", "ld", "readelf", "valgrind", "python3")}
        record["system_packages"] = run(
            ["dpkg-query", "-W", "libc6", "libc6-dev", "libc6-dbg", "valgrind"],
            "system-packages").splitlines()
        record["compiler_sha256"] = digest(Path(shutil.which("gcc")).resolve())
        record["static_inputs_sha256"] = {}
        for name in ("libc.a", "libgcc.a", "libgcc_eh.a", "crt1.o", "crti.o", "crtn.o", "crtbeginT.o", "crtend.o"):
            path = Path(run(["gcc", "-print-file-name=" + name], "locate-" + name).strip())
            if not path.is_file():
                raise RuntimeError("missing static toolchain input " + name)
            record["static_inputs_sha256"][str(path)] = digest(path)
        archive = work / "memtester-4.7.1.tar.gz"
        run(["curl", "--fail", "--location", "--proto", "=https", "--tlsv1.2",
             "--retry", "3", URL, "-o", archive], "download")
        if digest(archive) != SHA256 or archive.stat().st_size != 24590:
            raise RuntimeError("original source archive mismatch")
        record["source"] = {"url": URL, "sha256": SHA256, "size": 24590}
        with tarfile.open(archive) as source:
            source.extractall(work, filter="data")
        source = work / "memtester-4.7.1"
        checked = work / "checked"
        run(["python3", HERE / "check.py", "--source", source, "--work", checked,
             "--cc", "gcc", "--cflag=-g", "--cflag=-gdwarf-4"], "regression")
        shutil.copy2(checked / "verification.json", output / "regression.json")
        memcheck = ["valgrind", "--tool=memcheck", "--error-exitcode=97",
                    "--leak-check=full", "--show-leak-kinds=all",
                    "--errors-for-leak-kinds=all", "--track-origins=yes",
                    "--undef-value-errors=yes"]
        run([*memcheck, checked / "green"], "memcheck-regression")
        patched = checked / "patched"
        binary = output / "memtester"
        flags = ["-static", "-O2", "-g", "-gdwarf-4", "-Wall", "-Wextra",
                 "-fanalyzer", "-DPOSIX", "-D_POSIX_C_SOURCE=200809L",
                 "-D_FILE_OFFSET_BITS=64", "-DTEST_NARROW_WRITES"]
        run(["gcc", *flags, patched / "memtester.c", patched / "tests.c",
             "-o", binary], "static-build")
        data = binary.read_bytes()
        if data[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", data, 18)[0] != 183:
            raise RuntimeError("candidate is not little-endian ELF64 AArch64")
        if struct.unpack_from("<H", data, 16)[0] != 2:
            raise RuntimeError("candidate is not ET_EXEC")
        phoff = struct.unpack_from("<Q", data, 32)[0]
        phsize, phnum = struct.unpack_from("<HH", data, 54)
        types = [struct.unpack_from("<I", data, phoff + i * phsize)[0] for i in range(phnum)]
        if 3 in types or 2 in types:  # PT_INTERP or PT_DYNAMIC
            raise RuntimeError("candidate requires a dynamic loader")
        run(["readelf", "-h", "-l", "-d", binary], "elf")
        run([binary, "1M", "1"], "static-smoke")
        record["binary"] = {"sha256": digest(binary), "size": binary.stat().st_size,
                            "elf_machine": 183, "static": True}
        record["patched_source_sha256"] = {n: digest(patched / n) for n in ("memtester.c", "tests.c")}
        record["scripts_sha256"] = {n: digest(HERE / n) for n in ("check.py", "bitspread.c", "linux-candidate.py")}
        patch = PORTS / "pkgsrc/sysutils/memtester/patches/patch-tests.c"
        record["patch_sha256"] = digest(patch)
        record["patch_url"] = ("https://github.com/" + os.environ["GITHUB_REPOSITORY"] +
                               "/blob/" + record["ports_commit"] +
                               "/pkgsrc/sysutils/memtester/patches/patch-tests.c")
        (output / "SHA256SUMS").write_text(record["binary"]["sha256"] + "  memtester\n")
        inputs = output / "source"
        inputs.mkdir()
        shutil.copy2(archive, inputs / archive.name)
        shutil.copy2(patch, inputs / patch.name)
        shutil.copy2(source / "COPYING", output / "COPYING")
        libc_notice = Path("/usr/share/doc/libc6/copyright")
        if libc_notice.is_file():
            shutil.copy2(libc_notice, output / "libc-copyright")
        (output / "README.txt").write_text(
            "Linux AArch64 diagnostic candidate; GPL-2.0-only memtester 4.7.1.\n"
            "This is not an EmberBSD package or a physical RAM acceptance result.\n"
            "Source archive and the common Ports patch are in source/.\n"
            "Receipt records build commands, hashes, tool versions and native checks.\n"
            "Verify SHA256SUMS before use. No target device was used for compilation.\n")
        record["status"] = "pass"
        print("PASS: native AArch64 checks, strict Memcheck, static ELF and complete smoke")
        print("memtester SHA256", record["binary"]["sha256"])
    finally:
        (output / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
