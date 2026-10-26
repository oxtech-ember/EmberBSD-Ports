#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 The EmberBSD Project contributors.
# Developed with AI assistance.
"""Compile the actual common GCDA source in current and legacy libc ABI modes."""
import argparse
from pathlib import Path
import shlex
import struct
import subprocess
import tempfile


def expected(legacy):
    def words(*values):
        return b"".join(struct.pack("=I", value) for value in values)

    def counters(*values):
        tag = b"\0\0\xa1\1" if legacy else words(0x01a10000)
        data = tag + words(2 * len(values))
        for value in values:
            data += (struct.pack("=Q", value) if legacy else
                     words(value & 0xffffffff, value >> 32))
        return data

    tag = b"\0\0\0\1" if legacy else words(0x01000000)
    data = (b"adcg" if legacy else words(0x67636461))
    data += (b"*804" if legacy else words(0x3430382a)) + words(0x12345678)
    data += tag + words(8 if legacy else 3, 42, 0x11223344, 0x55667788)
    if legacy:
        data += words(4) + b"fixture_name\0\0\0\0"
    data += counters(14, 0x22446688aaccef10)
    data += tag + words(2 if legacy else 3, 43, 7)
    if not legacy:
        data += words(9)
    data += counters(6)
    if legacy:
        data += b"\0\0\0\xa1" + words(9, 0, 0, 2, 0, 0, 0, 0, 0, 0)
        data += b"\0\0\0\xa3" + words(0)
    else:
        data += words(0xa3000000, 3, 0, 0, 1)
    return data + bytes(8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", required=True, help="selected native C compiler")
    parser.add_argument("--source", required=True, type=Path, help="prepared LLVM root")
    parser.add_argument("--gcda", type=Path, help="candidate GCDA source; defaults to the prepared source")
    parser.add_argument("--cflags", default="", help="native compile/link options; supports sanitizers")
    args = parser.parse_args()
    profile = args.source.resolve() / "compiler-rt/lib/profile"
    gcda = args.gcda.resolve() if args.gcda else profile / "GCDAProfiling.c"
    fixture = Path(__file__).with_name("gcda-abi-fixture.c")
    with tempfile.TemporaryDirectory(prefix="gcda-abi-") as temporary:
        work = Path(temporary)
        for legacy in (False, True):
            name = "legacy" if legacy else "current"
            binary, output = work / name, work / (name + ".gcda")
            mode = ("-DCOMPILER_RT_LIBC_LEGACY_GCOV" if legacy else
                    "-DTEST_CURRENT_GCOV_ABI")
            common = [args.cc, *shlex.split(args.cflags), "-Wall", "-Werror",
                "-DCOMPILER_RT_HAS_FCNTL_LCK=1", "-DCOMPILER_RT_HAS_UNAME=1",
                "-I", str(profile), "-I", str(args.source.resolve() / "compiler-rt/include")]
            utility = work / (name + "-util.o")
            subprocess.run([*common, "-c", str(profile / "InstrProfilingUtil.c"),
                "-o", str(utility)], check=True)
            subprocess.run([*common, "-Wextra", mode, str(fixture), str(gcda),
                str(utility), "-o", str(binary)], check=True)
            subprocess.run([str(binary), str(output)], check=True)
            actual = output.read_bytes()
            if actual != expected(legacy):
                raise SystemExit(name + " GCDA byte format changed: " + actual.hex())
            print(name + ": exact file records, callbacks, boundaries and merge PASS")
            fault = work / (name + "-fdopen")
            subprocess.run([*common, "-Wextra", mode, "-Dfdopen=fixture_fdopen",
                str(fixture.with_name("gcda-fdopen-fixture.c")), str(gcda),
                str(utility), "-o", str(fault)], check=True)
            result = subprocess.run([str(fault), str(work / (name + "-failure.gcda"))],
                                    text=True, capture_output=True, check=True)
            if "cannot open stream" not in result.stderr:
                raise SystemExit(name + " missing fdopen failure diagnostic")
            print(name + ": fdopen failure and descriptor cleanup PASS")


if __name__ == "__main__":
    main()
