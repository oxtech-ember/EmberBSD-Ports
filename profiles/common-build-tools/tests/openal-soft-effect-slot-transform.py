#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the openal-soft effect slot transform against a target C++ library.

openal-soft 1.25.2 passed &ContextBase::EffectSlotCluster::operator* to
std::views::transform. The address of a standard library member function is
not portable, and LLVM libc++ rejects the call. The test applies the recipe
patches to alc/alc.cpp from the distfile, takes the transform argument and the
real EffectSlotCluster type, and compiles them with the given C++ compiler.
"""

import argparse
from pathlib import Path
import re
import subprocess
import tarfile

HARNESS = """#include <algorithm>
#include <array>
#include <memory>
#include <ranges>
#include <vector>
struct EffectSlotBase {{ int wet = 0; }};
struct ContextBase {{
    {cluster}
}};
void clear(std::vector<ContextBase::EffectSlotCluster> &clusters)
{{
    std::ranges::for_each(clusters
        | std::views::transform({argument})
        | std::views::join, [](EffectSlotBase &slot) {{ slot.wet = 0; }});
}}
"""


def call_argument(text, start):
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            if depth == 0:
                return text[start:index]
            depth -= 1
    raise SystemExit("FAIL: unterminated std::views::transform call")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--distfile", type=Path, required=True)
    parser.add_argument("--patch", required=True, help="patch(1) program")
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("cxx", nargs="+", help="target C++ compiler and flags")
    args = parser.parse_args()
    work = args.work.resolve()
    if work.exists():
        parser.error("Work directory already exists")
    work.mkdir(parents=True)
    names = ("alc/alc.cpp", "core/context.h")
    with tarfile.open(args.distfile.resolve(strict=True)) as archive:
        for member in archive.getmembers():
            name = member.name.split("/", 1)[-1]
            if name in names:
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
    patches = sorted((args.pkgsrc.resolve(strict=True) / "audio/openal-soft/patches")
                     .glob("patch-alc_alc.cpp*"))
    for patch in patches:
        subprocess.run([args.patch, "-p0", "-s", "-F", "0", "-i", str(patch)],
                       cwd=work, check=True, stdin=subprocess.DEVNULL)
    source = (work / "alc/alc.cpp").read_text()
    calls = [m.end() for m in re.finditer(r"for_each\(context->mEffectSlotClusters\s*"
                                         r"\|\s*std::views::transform\(", source)]
    if len(calls) != 1:
        print("FAIL: found %d effect slot transforms" % len(calls))
        raise SystemExit(1)
    argument = call_argument(source, calls[0])
    cluster = re.findall(r"using EffectSlotCluster = [^;]+;",
                         (work / "core/context.h").read_text())
    if len(cluster) != 1:
        print("FAIL: EffectSlotCluster type not found")
        raise SystemExit(1)
    harness = work / "transform.cpp"
    harness.write_text(HARNESS.format(cluster=cluster[0], argument=argument))
    result = subprocess.run(args.cxx + ["-std=c++20", "-fsyntax-only", str(harness)],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        print(result.stdout, end="")
        print("FAIL: the effect slot transform does not compile: %s" % argument.strip())
        raise SystemExit(1)
    print("PASS: openal-soft effect slot transform compiles")


if __name__ == "__main__":
    main()
