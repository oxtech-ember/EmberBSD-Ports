#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the actual RWStl float reader with UBSan.
"""Compile the original and patched source helper with native GCC16."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def helper(source):
    unit = source / "src/DataExchange/TKDESTL/RWStl/RWStl_Reader.cxx"
    text = unit.read_text()
    start = text.index("inline static float readStlFloat(const char* theData)")
    finish = text.index("//! Read a Little Endian 32 bits float\ninline static gp_XYZ", start)
    notice = text[:text.index("#include <RWStl_Reader.hxx>")]
    return notice + text[start:finish], hashlib.sha256(unit.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("patched", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("--cxx", required=True)
    parser.add_argument("--sysroot", type=Path)
    args = parser.parse_args()
    args.original = args.original.resolve(strict=True)
    args.patched = args.patched.resolve(strict=True)
    work = args.work.resolve()
    if not args.work.is_absolute() or work.exists():
        parser.error("Use a new absolute work directory")
    version = subprocess.check_output([args.cxx, "-dumpfullversion"], text=True).strip()
    identity = subprocess.check_output([args.cxx, "--version"], text=True)
    if not version.startswith("16.") or "GCC" not in identity:
        parser.error("Use native GCC16")
    work.mkdir(parents=True)
    flags = ["-std=c++17", "-O1", "-g", "-fno-omit-frame-pointer",
             "-fsanitize=undefined", "-fno-sanitize-recover=all", "-Wall", "-Wextra", "-Werror"]
    if args.sysroot is not None:
        flags.extend(("-isysroot", str(args.sysroot.resolve(strict=True))))
    prefix = """#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error This regression exercises the actual little-endian STL reader branch.
#endif
#define OCCT_BINARY_FILE_DO_INVERSE 0
static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
"""
    consumer = """int main(int argc, char** argv)
{
  alignas(float) char aStorage[sizeof(float) + 1];
  const unsigned char aBytes[4] = {0x00, 0x00, 0xa0, 0x3f};
  const bool isUnaligned = argc == 2 && std::strcmp(argv[1], "unaligned") == 0;
  char* aData = aStorage + (isUnaligned ? 1 : 0);
  std::memcpy(aData, aBytes, sizeof(aBytes));
  // Keep the actual reader call observable instead of folding the known input.
  float (*volatile aReader)(const char*) = &readStlFloat;
  const float aValue = aReader(aData);
  if (aValue != 1.25f)
    return 2;
  std::printf("value=1.25\\n");
  return 0;
}
"""
    records = []
    environment = dict(os.environ, UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    for label, source in (("before", args.original), ("after", args.patched)):
        body, digest = helper(source)
        unit = work / (label + ".cxx")
        binary = work / label
        unit.write_text(prefix + body + consumer)
        command = [args.cxx, *flags, str(unit), "-o", str(binary)]
        result = subprocess.run(command, capture_output=True, text=True)
        (work / (label + "-compile.log")).write_text(result.stdout + result.stderr)
        records.append({"variant": label, "source_sha256": digest,
                        "compile": command, "compile_exit": result.returncode})
        result.check_returncode()
        for mode in ("aligned", "unaligned"):
            result = subprocess.run([str(binary), mode], env=environment,
                                    capture_output=True, text=True)
            output = result.stdout + result.stderr
            (work / (label + "-" + mode + ".log")).write_text(output)
            causal = label == "before" and mode == "unaligned"
            if causal:
                if result.returncode == 0 or "misaligned address" not in output:
                    raise RuntimeError("The original reader did not expose its alignment defect")
            elif result.returncode != 0 or result.stdout != "value=1.25\n" or result.stderr:
                raise RuntimeError(label + " " + mode + " failed")
            records.append({"variant": label, "mode": mode,
                            "exit": result.returncode, "causal_failure": causal})
    (work / "results.json").write_text(json.dumps({
        "compiler": identity, "version": version, "flags": flags,
        "scope": "Actual extracted readStlFloat; little-endian branch; no replacement implementation",
        "results": records,
    }, indent=2) + "\n")
    print("PASS: original unaligned load fails UBSan; patched aligned and unaligned reads retain 1.25")


if __name__ == "__main__":
    main()
