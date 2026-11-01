#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check Blink Vector layout against Abseil's annotation macro collision."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


VECTOR_HEADER = "third_party/blink/renderer/platform/wtf/vector.h"


def run(argv, *, cwd, label):
    result = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise RuntimeError(label + " failed with exit " + str(result.returncode) +
                           "\n" + result.stderr)
    return result
def compile_argv(command, source, obj, depfile, source_root, foreign_header,
                 expect_asan, vfs_overlay):
    result = []
    skip_next = False
    for token in command:
        if skip_next:
            skip_next = False
            continue
        if token in ("-MF", "-MT", "-MQ", "-o"):
            skip_next = True
            continue
        if token.endswith(".cc") and "compositor_animation.cc" in token:
            continue
        if token.startswith("-DADDRESS_SANITIZER") or token.startswith("-UADDRESS_SANITIZER"):
            continue
        result.append(token)
    result.extend(["-I", str(source_root),
                   "-I", str(foreign_header.parents[3]),
                   "-DEXPECT_ASAN=" + ("1" if expect_asan else "0")])
    if expect_asan:
        result.extend(["-DADDRESS_SANITIZER", "-DARCH_CPU_X86_64"])
    if vfs_overlay:
        result.extend(["-ivfsoverlay", str(vfs_overlay)])
    result.extend(["-MF", str(depfile), "-MT", str(obj),
                   str(source), "-o", str(obj)])
    return result


def source_text(foreign_header, include_order):
    foreign_include = '#include "' + str(foreign_header).replace("\\", "\\\\").replace('"', '\\"') + '"\n'
    vector_include = '#include "' + VECTOR_HEADER + '"\n'
    includes = (foreign_include + vector_include if include_order == "foreign-first"
                else vector_include + foreign_include)
    return (
        includes
        + "#ifndef ANNOTATE_CONTIGUOUS_CONTAINER\n"
        + '#error "selected Abseil header did not expose its function-like macro"\n'
        + "#endif\n"
        + "#if EXPECT_ASAN\n"
        + "#ifndef WTF_ANNOTATE_CONTIGUOUS_CONTAINER\n"
        + '#error "ASan platform predicate did not enable the Blink sentinel"\n'
        + "#endif\n"
        + "static_assert(sizeof(blink::Vector<int, 4>) == sizeof(blink::Vector<int, 0>));\n"
        + "#else\n"
        + "#ifdef WTF_ANNOTATE_CONTIGUOUS_CONTAINER\n"
        + '#error "Blink sentinel must be disabled without ASan"\n'
        + "#endif\n"
        + "static_assert(sizeof(blink::Vector<int, 4>) > sizeof(blink::Vector<int, 0>));\n"
        + "#endif\n"
        + "int main() { return 0; }\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command-json", type=Path, required=True,
                        help="saved selected production C++ command JSON")
    parser.add_argument("--cwd", type=Path, required=True,
                        help="existing GN output directory used by the saved command")
    parser.add_argument("--source-root", type=Path, required=True,
                        help="prepared Chromium src tree with the ordered Ports patch series")
    parser.add_argument("--foreign-header", type=Path, required=True,
                        help="selected Abseil dynamic_annotations.h")
    parser.add_argument("--vfs-overlay", type=Path,
                        help="optional diagnostic overlay for patched production headers")
    args = parser.parse_args()
    command_data = json.loads(args.command_json.read_text())
    command = command_data.get("command_argv")
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise RuntimeError("saved command JSON has no string command_argv")
    cwd = args.cwd.resolve(strict=True)
    source_root = args.source_root.resolve(strict=True)
    foreign_header = args.foreign_header.resolve(strict=True)
    overlay = args.vfs_overlay.resolve(strict=True) if args.vfs_overlay else None
    if not (source_root / VECTOR_HEADER).is_file() or not foreign_header.is_file():
        raise RuntimeError("prepared Vector or selected foreign annotation header is missing")
    if not Path(command[0]).is_file():
        raise RuntimeError("saved selected compiler wrapper is missing")

    with tempfile.TemporaryDirectory(prefix="blink-vector-sentinel-") as temporary:
        root = Path(temporary)
        for enabled in (False, True):
            for order in ("foreign-first", "blink-first"):
                stem = f"layout-{int(enabled)}-{order}"
                source = root / (stem + ".cc")
                obj = root / (stem + ".o")
                depfile = root / (stem + ".d")
                source.write_text(source_text(foreign_header, order))
                argv = compile_argv(command, source, obj, depfile, source_root,
                                    foreign_header, enabled, overlay)
                run(argv, cwd=cwd, label=stem)
                if not obj.is_file() or obj.stat().st_size == 0:
                    raise RuntimeError("selected compiler produced no object for " + stem)

    print("real Blink Vector layout passes for Abseil-before/after and ASan predicate on/off")


if __name__ == "__main__":
    main()
