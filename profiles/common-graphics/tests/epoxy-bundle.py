#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real bundle and installed-payload refusal tests.
import errno
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def link_or_copy(source, target):
    try:
        os.link(source, target)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        shutil.copy2(source, target)


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: epoxy-bundle.py BUNDLE SYSROOT NEW_WORK")
    bundle, sysroot = (Path(arg).resolve(strict=True) for arg in sys.argv[1:3])
    work = Path(sys.argv[3])
    if not work.is_absolute() or work.exists() or work.is_symlink():
        raise SystemExit("NEW_WORK must be new and absolute")
    work.mkdir(parents=True)
    runner = bundle / "run-epoxy-tests.sh"

    def check(name, expected, command):
        result = subprocess.run([str(arg) for arg in command], capture_output=True, text=True, timeout=300, check=False)
        output = result.stdout + result.stderr
        (work / (name + ".log")).write_text(output)
        if not (result.returncode == 0 if expected is None else result.returncode != 0 and expected in output):
            raise SystemExit("FAIL: " + name)
        print("PASS: " + name)

    check("original", None, ["sh", runner, "--verify-sysroot", bundle, sysroot])
    changed = work / "changed-bundle"
    shutil.copytree(bundle, changed, symlinks=True)
    with (changed / "bin/epoxy-render").open("ab") as stream:
        stream.write(b"modified actual ELF")
    check("changed-elf", "Bundle drift: bin/epoxy-render",
          ["sh", changed / "run-epoxy-tests.sh", changed, work / "must-not-run"])
    if (work / "must-not-run").exists():
        raise SystemExit("target execution started after artifact corruption")
    shutil.rmtree(changed)
    fixture = work / "sysroot-fixture"

    def installed(path):
        if not path.startswith("/usr/pkg/") or ".." in PurePosixPath(path).parts:
            raise SystemExit("unsafe installed fixture path")
        return fixture / path.removeprefix("/")

    paths = set()
    for name in ("installed-files.sha256", "runtime-libraries.sha256"):
        paths.update(line.split("  ", 1)[1] for line in (bundle / name).read_text().splitlines())
    for path in sorted(paths):
        destination = installed(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        link_or_copy((sysroot / path.removeprefix("/")).resolve(strict=True), destination)
    for line in (bundle / "installed-links.tsv").read_text().splitlines():
        path, target = line.split("\t", 1)
        destination = installed(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.unlink(missing_ok=True)
        destination.symlink_to(target)
    check("original-file-fixture", None, ["sh", runner, "--verify-sysroot", bundle, fixture])
    for index, path in enumerate(("/usr/pkg/include/epoxy/gl.h", "/usr/pkg/lib/libepoxy.so.0.0.0")):
        source = sysroot / path.removeprefix("/")
        original_hash = digest(source)
        destination = installed(path)
        # Atomic replacement never writes through a hard link into the source sysroot.
        replacement = Path(str(destination) + ".changed")
        replacement.write_bytes(destination.read_bytes() + b"changed installed payload")
        replacement.replace(destination)
        check("installed-drift-" + str(index), "Installed drift:", ["sh", runner, "--verify-sysroot", bundle, fixture])
        if digest(source) != original_hash:
            raise SystemExit("source sysroot was changed")
        destination.unlink()
        link_or_copy(source, destination)
    shutil.rmtree(fixture)
    print("PASS: five real-artifact integrity cases; no target code executed and source sysroot unchanged")


if __name__ == "__main__":
    main()
