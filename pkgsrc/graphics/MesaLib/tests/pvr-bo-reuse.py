#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Run actual Mesa BO allocation code with a deterministic winsys backend."""
import argparse
from pathlib import Path
import re
import subprocess


def function(source, name):
    matches = re.finditer(r"^(?:static\s+)?(?:inline\s+)?(?:void\s*\*?|bool|VkResult|uint32_t|struct pvr_bo\s*\*)\s*" + name + r"\s*\(", source, re.M)
    match = next((m for m in matches if source.index("{", m.end()) < source.index(";", m.end())), None)
    if not match:
        raise ValueError("missing function: " + name)
    start = source.index("{", match.end())
    depth = 0
    for end in range(start, len(source)):
        depth += (source[end] == "{") - (source[end] == "}")
        if not depth:
            return source[match.start():end + 1]
    raise ValueError("unclosed function: " + name)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--mesa", required=True, type=Path)
    parser.add_argument("--cc", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    root = args.mesa / "src/imagination/vulkan"
    source = (root / "pvr_bo.c").read_text()
    header = re.sub(r"^#include.*\n", "", (root / "pvr_bo.h").read_text(), flags=re.M)
    template = Path(__file__).with_suffix(".c").read_text()
    names = ["pvr_bo_alloc_to_winsys_flags", "pvr_bo_alloc", "pvr_bo_free",
             "pvr_bo_suballocator_init", "pvr_bo_suballocator_fini", "pvr_bo_get_ref",
             "pvr_bo_suballoc", "pvr_bo_suballoc_free", "pvr_bo_suballoc_get_map_addr"]
    names += re.findall(r"^(?:static\s+)?(?:inline\s+)?(?:void|bool|struct pvr_bo\s*\*)\s*(pvr_bo_cache_\w+|pvr_bo_destroy)\s*\(", source, re.M)
    # Keep the production declaration order. Helpers may call pvr_bo_destroy.
    bodies = sorted({function(source, name) for name in names}, key=source.index)
    limits = "\n".join(re.findall(r"^#define PVR_BO_CACHE_.*", source, re.M))
    code = template.replace("/* HEADER */", header).replace("/* SOURCE */", limits + "\n" + "\n\n".join(bodies))
    out = args.work / "contract.c"
    out.write_text(code)
    command = [str(args.cc), "-std=gnu11", "-g", "-O1", "-Wall", "-Wextra", "-Werror",
               "-Wno-unused-function", "-Wno-unused-parameter", "-pthread",
               "-I" + str(args.mesa / "src"), str(out), "-o", str(args.work / "contract")]
    if args.sanitize:
        command[1:1] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    subprocess.run(command, check=True)
    subprocess.run([str(args.work / "contract")], check=True)


if __name__ == "__main__":
    main()
