#!/usr/bin/env python3
"""Check dependency source candidates without compiling or changing pkgsrc."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile


def apply_exact(original, patch):
    """Apply one unified file diff in memory, with no offset or fuzz."""
    lines = original.splitlines(keepends=True)
    diff = patch.splitlines(keepends=True)
    output = []
    cursor = 0
    hunks = 0
    i = 0
    while i < len(diff):
        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", diff[i])
        if not match:
            i += 1
            continue
        start, old_count, new_start, new_count = (
            int(match[1]), int(match[2] or 1),
            int(match[3]), int(match[4] or 1))
        index = start - 1 if old_count else start
        if index < cursor:
            raise ValueError("overlapping patch hunks")
        output.extend(lines[cursor:index])
        if len(output) != (new_start - 1 if new_count else new_start):
            raise ValueError("new hunk offset differs")
        cursor = index
        removed = added = 0
        i += 1
        while removed < old_count or added < new_count:
            line = diff[i]
            i += 1
            if line[0] in " -":
                if cursor >= len(lines) or lines[cursor] != line[1:]:
                    raise ValueError("source differs from exact patch context")
                cursor += 1
                removed += 1
            if line[0] in " +":
                output.append(line[1:])
                added += 1
            if line[0] not in " +-" or removed > old_count or added > new_count:
                raise ValueError("invalid patch hunk")
        hunks += 1
    if not hunks:
        raise ValueError("patch has no hunks")
    return "".join(output + lines[cursor:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--bluezqt-archive", type=Path, required=True)
    args = parser.parse_args()
    owner = Path(__file__).resolve().parent
    pins = json.loads((owner / "dependency-sources.json").read_text())
    revision = subprocess.check_output(
        ["git", "-C", str(args.pkgsrc), "rev-parse", "HEAD"], text=True).strip()
    assert revision == pins["pkgsrc_revision"], revision
    archive = args.bluezqt_archive.read_bytes()
    assert hashlib.sha256(archive).hexdigest() == pins["sources"][1]["sha256"]
    bluezqt = owner / "recipes/comms/kf6-bluez-qt"
    contexts = []
    with tarfile.open(args.bluezqt_archive) as source:
        for patch in sorted((bluezqt / "patches").iterdir()):
            text = patch.read_text()
            name = re.search(r"^--- (.+)\.orig$", text, re.MULTILINE)[1]
            original = source.extractfile("bluez-qt-6.31.0/" + name).read().decode()
            changed = apply_exact(original, text)
            assert changed != original
            # A changed source context must be rejected, not silently relocated.
            try:
                apply_exact("deliberate invalid first line\n" + original, text)
            except ValueError:
                pass
            else:
                raise AssertionError("changed-context control was accepted")
            contexts.append(name)
    webengine = owner / "recipes/www/qt6-qtwebengine"
    original = args.pkgsrc / "www/qt6-qtwebengine"
    differences = sorted(str(p.relative_to(original)) for p in original.rglob("*")
                         if p.is_file() and p.read_bytes() !=
                         (webengine / p.relative_to(original)).read_bytes())
    assert differences == ["Makefile", "PLIST", "buildlink3.mk", "distinfo",
                           "patches/patch-configure.cmake"], differences
    assert sorted(p.name for p in (original / "patches").iterdir()) == sorted(
        p.name for p in (webengine / "patches").iterdir())
    patch_count = len(list((original / "patches").iterdir()))
    for recipe in [bluezqt, webengine]:
        distinfo = (recipe / "distinfo").read_text()
        for patch in (recipe / "patches").iterdir():
            payload = b"".join(line for line in patch.read_bytes().splitlines(keepends=True)
                               if b"$NetBSD" not in line)
            expected = re.search(r"^SHA1 \(" + re.escape(patch.name) +
                                 r"\) = ([0-9a-f]+)$", distinfo, re.MULTILINE)[1]
            assert hashlib.sha1(payload).hexdigest() == expected, patch
    assert "rm:-Wl,--fatal-warnings" not in (webengine / "Makefile").read_text()
    assert "-DQT_FEATURE_webengine_vulkan=OFF" not in (webengine / "Makefile").read_text()
    assert "+#qt_webengine_configure_check(\"glibc\"" not in (
        webengine / "patches/patch-configure.cmake").read_text()
    assert "-DKF_IGNORE_PLATFORM_CHECK=OFF" in (bluezqt / "Makefile").read_text()
    print(json.dumps({"status": "PASS", "scope": "source preparation only; no compilation",
                      "pkgsrc_revision": revision, "bluezqt_sha256": hashlib.sha256(archive).hexdigest(),
                      "bluezqt_exact_patch_contexts": contexts, "changed_context_controls": len(contexts),
                      "webengine_inherited_patch_count": patch_count,
                      "webengine_changed_files": differences,
                      "all_candidate_patch_checksums": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
