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


def linux_rfkill_projection(text):
    """Select only Q_OS_LINUX branches; preserve all other source bytes."""
    stack = []
    output = []
    active = True
    for line in text.splitlines(keepends=True):
        match = re.match(r"#(ifdef|ifndef) Q_OS_LINUX\s*$", line)
        if match:
            condition = match[1] == "ifdef"
            stack.append(("linux", active, condition))
            active = active and condition
        elif re.match(r"#if(?:def|ndef)?\b", line):
            stack.append(("other", active, True))
            if active:
                output.append(line)
        elif line.startswith("#else") and stack and stack[-1][0] == "linux":
            kind, parent, condition = stack[-1]
            stack[-1] = (kind, parent, not condition)
            active = parent and not condition
        elif line.startswith("#endif") and stack:
            kind, parent, _ = stack.pop()
            if kind == "other" and active:
                output.append(line)
            active = parent
        elif active:
            output.append(line)
    if stack:
        raise ValueError("unbalanced source platform guards")
    return "".join(output)


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
    parser.add_argument("--webengine-archive", type=Path)
    parser.add_argument("--webchannel-archive", type=Path)
    args = parser.parse_args()
    owner = Path(__file__).resolve().parent
    repository = owner.parents[1]
    tracked = set(subprocess.check_output([
        "git", "-C", str(repository), "ls-files", "-z",
        "probes/plasma-bigscreen/recipes"], text=True).split("\0"))
    recipe_inputs = sorted(str(path.relative_to(repository))
                           for path in (owner / "recipes").rglob("*")
                           if path.is_file())
    missing = sorted(set(recipe_inputs) - tracked)
    if missing:
        raise ValueError("recipe inputs are absent from Git: " + ", ".join(missing))
    pins = json.loads((owner / "dependency-sources.json").read_text())
    archive_checks = {}
    for recipe, archive_path in [("www/qt6-qtwebengine", args.webengine_archive),
                                 ("www/qt6-qtwebchannel", args.webchannel_archive)]:
        if archive_path is None:
            continue
        pin = next(item for item in pins["sources"] if item["recipe"] == recipe)
        assert archive_path.stat().st_size == pin["size"], archive_path
        for algorithm in ["sha256", "sha512", "blake2s"]:
            with archive_path.open("rb") as stream:
                actual = hashlib.file_digest(stream, algorithm).hexdigest()
            assert actual == pin[algorithm], (archive_path, algorithm)
        archive_checks[recipe] = "SHA256, SHA512, BLAKE2s and size match"
    revision = subprocess.check_output(
        ["git", "-C", str(args.pkgsrc), "rev-parse", "HEAD"], text=True).strip()
    assert revision == pins["pkgsrc_revision"], revision
    archive = args.bluezqt_archive.read_bytes()
    assert hashlib.sha256(archive).hexdigest() == pins["sources"][1]["sha256"]
    bluezqt = owner / "recipes/comms/kf6-bluez-qt"
    contexts = []
    linux_unchanged = []
    with tarfile.open(args.bluezqt_archive) as source:
        for patch in sorted((bluezqt / "patches").iterdir()):
            text = patch.read_text()
            name = re.search(r"^--- (.+)\.orig$", text, re.MULTILINE)[1]
            original = source.extractfile("bluez-qt-6.31.0/" + name).read().decode()
            changed = apply_exact(original, text)
            assert changed != original
            if name in ["src/rfkill.cpp", "src/rfkill_p.h"]:
                assert linux_rfkill_projection(original) == linux_rfkill_projection(changed)
                linux_unchanged.append(name)
            elif name == "src/a2dp-codecs.h":
                projected = re.sub(r"#if defined\(__NetBSD__\).*?#endif\n",
                                   "#include <endian.h>\n", changed, count=1, flags=re.DOTALL)
                for before, after in [("BLUEZQT_BYTE_ORDER", "__BYTE_ORDER"),
                                      ("BLUEZQT_LITTLE_ENDIAN", "__LITTLE_ENDIAN"),
                                      ("BLUEZQT_BIG_ENDIAN", "__BIG_ENDIAN")]:
                    projected = projected.replace(before, after)
                assert projected == original
                linux_unchanged.append(name)
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
    configure_patch = (webengine / "patches/patch-configure.cmake").read_text()
    target_lines = "".join(line[1:] for line in configure_patch.splitlines(keepends=True)
                           if line.startswith((" ", "+")) and not line.startswith("+++"))
    glibc_block = ('qt_webengine_configure_check("glibc"\n'
        '    MODULES QtWebEngine\n'
        '    CONDITION NOT LINUX OR TEST_glibc\n'
        '    MESSAGE "A suitable version >= ${QT_CONFIGURE_CHECK_glibc_version} of glibc is required."\n'
        '    DOCUMENTATION "Glibc library at least ${QT_CONFIGURE_CHECK_glibc_version} version or later."\n'
        '    TAGS LINUX_PLATFORM\n)')
    assert target_lines.count(glibc_block) == 1, "Linux glibc check must stay active"
    toolchains = (webengine / "patches/patch-cmake_QtToolchainHelpers.cmake").read_text()
    assert '+    elseif(NETBSD)\n+        set(${result} "netbsd" PARENT_SCOPE)' in toolchains
    assert 'is_gcc CONDITION UNIX AND CMAKE_CXX_COMPILER_ID STREQUAL "GNU"' in toolchains
    assert "-DKF_IGNORE_PLATFORM_CHECK=OFF" in (bluezqt / "Makefile").read_text()
    print(json.dumps({"status": "PASS", "scope": "source preparation only; no compilation",
                      "tracked_recipe_inputs": len(recipe_inputs),
                      "pkgsrc_revision": revision, "bluezqt_sha256": hashlib.sha256(archive).hexdigest(),
                      "optional_archive_checks": archive_checks,
                      "bluezqt_exact_patch_contexts": contexts, "changed_context_controls": len(contexts),
                      "bluezqt_linux_source_unchanged": linux_unchanged,
                      "webengine_inherited_patch_count": patch_count,
                      "webengine_linux_glibc_check": "active",
                      "webengine_netbsd_gn_target": "netbsd/GNU",
                      "webengine_changed_files": differences,
                      "all_candidate_patch_checksums": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
