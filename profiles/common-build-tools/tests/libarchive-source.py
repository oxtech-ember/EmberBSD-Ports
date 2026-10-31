#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real pkgsrc source-import regression.
"""Verify the complete shared libarchive import without compiling target code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pkgsrc", "archive", "bmake", "work"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    source = Path(args.pkgsrc).resolve(strict=True)
    archive = Path(args.archive).resolve(strict=True)
    bmake = Path(args.bmake).resolve(strict=True)
    work = Path(args.work).resolve()
    require(not work.exists(), "Work directory already exists.")
    require(hashlib.sha256(archive.read_bytes()).hexdigest() ==
            "a3dc0872b1b39da34dc18ef1b944f0f11ffd37425d70ae04be679279f1cf43d2",
            "The official libarchive 3.8.11 archive hash differs.")
    work.mkdir(parents=True)
    tree = work / "pkgsrc"
    # Copy only the actual shared provider and its source-copy consumers.
    selected = ("archivers/libarchive", "archivers/bsdtar", "pkgtools/pkg_install", "archivers/pixz")
    for name in selected:
        shutil.copytree(source / name, tree / name, copy_function=shutil.copy)
    commands = []

    def run(label, argv, cwd=tree, data=None):
        result = subprocess.run([str(x) for x in argv], cwd=cwd, input=data,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=dict(os.environ, LC_ALL="C"), timeout=60)
        (work / (label + ".stdout")).write_bytes(result.stdout)
        (work / (label + ".stderr")).write_bytes(result.stderr)
        commands.append(dict(label=label, argv=[str(x) for x in argv], status=result.returncode))
        (work / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(result.returncode == 0, f"{label} failed; inspect {work}.")
        return result.stdout

    patches = ("pkgsrc-libarchive-3.8.10-import.patch", "pkgsrc-libarchive-3.8.10.patch",
               "pkgsrc-libarchive-bmake.patch", "pkgsrc-libarchive-3.8.11.patch")
    pins = dict(line.split("\t")[:2] for line in
                (root / "profiles/common-build-tools/sources.tsv").read_text().splitlines()
                if line and not line.startswith("#"))
    verified = 0
    for name in patches:
        patch = root / "profiles/common-build-tools/patches" / name
        require(hashlib.sha256(patch.read_bytes()).hexdigest() == pins[name], "Pinned patch hash differs.")
        run(name + "-check", ["git", "apply", "--check", patch])
        run(name, ["git", "apply", patch])
        # Git's postimage IDs cover every changed text and binary file.
        for section in patch.read_text().split("diff --git ")[1:]:
            path = section.splitlines()[0].split(" b/", 1)[1]
            require(path.startswith("archivers/libarchive/"), "Unexpected patch scope.")
            match = re.search(r"^index [0-9a-f]+\.\.([0-9a-f]+)", section, re.M)
            require(match is not None, "Missing Git postimage ID.")
            digest = match[1]
            target = tree / path
            if set(digest) == {"0"}:
                require(not target.exists(), "Deleted source remains.")
            else:
                require(target.is_file() and blob(target.read_bytes()).startswith(digest),
                        "Git postimage differs: " + path)
            verified += 1
    vendor = tree / "archivers/libarchive/files"
    # An update-only CVS commit lacks new source/test files. Check the full
    # official payload, including every upstream regression input.
    absent = []
    upstream_tests = 0
    with tarfile.open(archive) as package:
        for member in package:
            relative = Path(member.name).relative_to("libarchive-3.8.11")
            if not member.isfile():
                continue
            if relative.parts[0] in ("libarchive", "libarchive_fe", "tar", "cpio", "cat", "unzip", "test_utils"):
                if not (vendor / relative).is_file():
                    absent.append(str(relative))
                if "test" in relative.parts:
                    upstream_tests += 1
    require(not absent, "Missing upstream payload: " + ", ".join(absent))
    common = (tree / "archivers/libarchive/Makefile.common").read_text()
    require("libarchive-3.8.11" in common and "TEST_TARGET=\t\tcheck" in common,
            "Shared version or upstream test target differs.")
    for consumer in ("archivers/bsdtar", "pkgtools/pkg_install"):
        recipe = (tree / consumer / "Makefile").read_text()
        require("${.CURDIR}/../../archivers/libarchive/files" in recipe and
                "${CP} -R ${FILESDIR.libarchive}" in recipe, "Shared source owner lost: " + consumer)
    require('"../../archivers/libarchive/buildlink3.mk"' in
            (tree / "archivers/pixz/Makefile").read_text(), "pixz lost its shared library dependency.")
    original = (vendor / "Makefile.in").read_text()
    companion = root / "profiles/common-build-tools/patches/pkgsrc-libarchive-consumers.patch"
    run("generated-bmake-check", ["patch", "--dry-run", "-f", "-p1", "-F", "0", "-i", companion])
    run("generated-bmake", ["patch", "-f", "-p1", "-F", "0", "-i", companion])
    require("PKGREVISION=\t\t4" in (tree / "pkgtools/pkg_install/Makefile").read_text(),
            "The rebuilt package-tools payload must have a new revision.")
    require((tree / "archivers/bsdtar/Makefile").read_bytes() ==
            (source / "archivers/bsdtar/Makefile").read_bytes(), "The common-zlib delta changed.")
    updated = (vendor / "Makefile.in").read_text()
    checks = 0
    for subdir, name in (("libarchive", "libarchive"), ("tar", "bsdtar"),
                         ("cpio", "bsdcpio"), ("cat", "bsdcat"), ("unzip", "bsdunzip")):
        target = subdir + "/test/list.h"
        pattern = r"^" + re.escape(target) + r":[^\n]*\n(?:\t[^\n]*\n)+"
        actual = re.search(pattern, updated, re.M)[0]
        before = re.search(pattern, original, re.M)[0]
        test = next(p for p in sorted((vendor / subdir / "test").glob("*.c"))
                    if "DEFINE_TEST(" in p.read_text())
        expected = "\n".join(sorted(line for line in test.read_text().splitlines()
                                   if line.startswith("DEFINE_TEST("))) + "\n"
        for state, recipe in (("before", before), ("after", actual)):
            build = work / (name + "-" + state)
            build.mkdir()
            makefile = build / "Makefile"
            makefile.write_text(f"MKDIR_P=mkdir -p\n{name}_test_SOURCES={test}\n" + recipe)
            run(name + "-" + state, [bmake, "-f", makefile, target], cwd=build, data=b"")
            output = (build / target).read_text()
            if state == "after":
                require(output == expected, "Actual bmake test-list generation differs: " + name)
            # Old bmake silently reads stdin for $^. New bmake supports $^;
            # record whether this host demonstrates the original defect.
            else:
                commands[-1]["detects_original_defect"] = output != expected
        checks += 1
    result = dict(scope="Source import, upstream test preservation and real bmake generation; no compilation or target execution.",
                  git_postimages=verified, upstream_test_files=upstream_tests, bmake_test_lists=checks)
    (work / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    (work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS:", json.dumps(result))


if __name__ == "__main__":
    main()
