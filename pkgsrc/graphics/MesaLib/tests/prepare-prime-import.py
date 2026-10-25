#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted). Prepare actual-source controls.
"""Prepare C fixtures from pinned Mesa source; do not select or run a compiler."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile


FILES = (
    "src/gallium/drivers/llvmpipe/lp_texture.c",
    "src/gallium/drivers/llvmpipe/lp_texture.h",
    "src/gallium/winsys/sw/kms-dri/kms_dri_sw_winsys.c",
)
PATCHES = (
    "patch-src_gallium_drivers_llvmpipe_lp__texture.c",
    "patch-src_gallium_winsys_sw_kms-dri_kms__dri__sw__winsys.c",
)


def digest(path, algorithm="sha256"):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def function(source, name):
    matches = list(re.finditer(r"^static [^\n]+\n" + re.escape(name) +
                              r"\(.*?^}\n", source, re.M | re.S))
    if len(matches) != 1:
        raise ValueError("Expected one actual function: " + name)
    match = matches[0]
    # Preserve the enclosing upstream conditions as well as the function body.
    # This makes the non-Linux test exercise the real platform guards.
    stack = []
    for line in source[:match.start()].splitlines():
        if re.match(r"^#\s*(if|ifdef|ifndef)\b", line):
            stack.append([line])
        elif re.match(r"^#\s*(else|elif)\b", line):
            stack[-1].append(line)
        elif re.match(r"^#\s*endif\b", line):
            stack.pop()
    return ("\n".join(line for level in stack for line in level) + "\n" +
            match[0] + "#endif\n" * len(stack))


def declaration(source, kind, name):
    matches = re.findall(r"^" + kind + " " + name + r"\n\{.*?^};\n",
                         source, re.M | re.S)
    if len(matches) != 1:
        raise ValueError("Expected one actual declaration: " + name)
    return matches[0]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("archive", type=Path)
    cli.add_argument("work", type=Path)
    cli.add_argument("--patch-tool", type=Path, required=True,
                     help="absolute source-regression patch tool; not an SDK provider")
    args = cli.parse_args()
    archive = args.archive.resolve(strict=True)
    tool = args.patch_tool
    work = args.work
    if not tool.is_absolute() or not tool.is_file():
        raise ValueError("Use an existing absolute --patch-tool")
    if not work.is_absolute() or work.exists() or work.is_symlink():
        raise ValueError("Use a new absolute work directory")
    recipe = Path(__file__).resolve().parent.parent
    distinfo = (recipe / "distinfo").read_text()
    expected = re.findall(r"^SHA512 \(mesa-26\.2\.5\.tar\.xz\) = (\w+)$",
                          distinfo, re.M)
    if len(expected) != 1 or digest(archive, "sha512") != expected[0]:
        raise ValueError("Archive does not match the canonical Mesa distinfo")
    for name in PATCHES:
        expected_patch = re.findall(r"^SHA1 \(" + re.escape(name) +
                                    r"\) = (\w+)$", distinfo, re.M)
        if expected_patch != [digest(recipe / "patches" / name, "sha1")]:
            raise ValueError("Patch does not match distinfo: " + name)
    work.mkdir(parents=True)
    before, after = work / "before", work / "after"
    with tarfile.open(archive) as bundle:
        for name in FILES:
            target = before / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.extractfile("mesa-26.2.5/" + name).read())
    shutil.copytree(before, after)
    for name in PATCHES:
        result = subprocess.run([str(tool), "-f", "-p0", "-F0", "-d", str(after),
                                 "-i", str(recipe / "patches" / name)],
                                capture_output=True, text=True, check=False)
        (work / (name + ".log")).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise ValueError("Source patch failed: " + name)
    hashes = {}
    for label, source in (("before", before), ("after", after)):
        lp, header, kms = [(source / name).read_text() for name in FILES]
        layouts = declaration(header, "enum", "llvmpipe_memory_fd_type")
        layouts += declaration(header, "struct", "llvmpipe_memory_allocation")
        for name in ("kms_sw_plane", "kms_sw_displaytarget", "kms_sw_winsys"):
            layouts += declaration(kms, "struct", name)
        (source / "layouts.h").write_text(layouts)
        bodies = "".join(function(lp, name) for name in (
            "llvmpipe_dmabuf_free", "llvmpipe_dmabuf_import",
            "llvmpipe_import_memory_fd", "llvmpipe_free_memory_fd"))
        bodies += "".join(function(kms, name) for name in (
            "kms_sw_displaytarget_add_from_prime",
            "kms_sw_displaytarget_create_mapped"))
        (source / "bodies.h").write_text(bodies)
        hashes[label] = {name: digest(source / name) for name in FILES}
    # These unrelated Linux allocation and export bodies and guards must stay exact.
    for name in ("llvmpipe_dmabuf_alloc", "llvmpipe_allocate_memory_fd",
                 "llvmpipe_resource_get_handle"):
        if function((before / FILES[0]).read_text(), name) != function(
                (after / FILES[0]).read_text(), name):
            raise ValueError("Linux allocation/export changed: " + name)
    (work / "prepared.json").write_text(json.dumps({
        "archive_sha256": digest(archive), "source_files": hashes,
        "patch_sha256": {name: digest(recipe / "patches" / name) for name in PATCHES},
        "fixture_sha256": digest(recipe / "tests/prime-import.c"),
        "scope": "Source preparation only; no compilation or execution",
    }, indent=2) + "\n")
    print("Prepared before/after actual-source fixtures. No compiler was run.")


if __name__ == "__main__":
    main()
