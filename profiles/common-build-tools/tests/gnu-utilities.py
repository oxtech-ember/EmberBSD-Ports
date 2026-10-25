#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the common GNU utility source delta. Do not run release scripts."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location('ports_exporter', ROOT / 'scripts/prepare-pkgsrc.py')
EXPORTER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(EXPORTER)
RELEASES = (("devel/diffutils", "diffutils-3.12"),
            ("sysutils/findutils", "findutils-4.11.0"))
GUARD_FROM = 'e) if test "`echo 1 2 3 | xargs -n2 echo`" = "1 2\n3"'
GUARD_TO = ('e) if command -v xargs >/dev/null 2>&1 && '
            'test "`echo 1 2 3 | xargs -n2 echo`" = "1 2\n3"')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def patch_run(patch_tool, patch, work, *options):
    command = [str(patch_tool), "--batch", "--fuzz=0",
               "--no-backup-if-mismatch", "-p0", *options, "-i", str(patch)]
    return subprocess.run(command, cwd=work, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=False)


def run(args):
    require(args.patch.is_absolute() and args.patch.is_file(),
            "Pass an explicit host GNU patch for source-data checks")
    require(args.work.is_absolute() and not args.work.exists(),
            "Use a new absolute caller-owned source work directory")
    args.work.mkdir()
    reports = []
    for (recipe, release), archive in zip(RELEASES, args.archives):
        path = ROOT / "pkgsrc" / recipe
        info = (path / "distinfo").read_text()
        require(archive.is_absolute(), "Use an absolute source archive path")
        size = re.search(r"^Size \(" + re.escape(release)
                         + r"\.tar\.xz\) = ([0-9]+) bytes$", info, re.M)
        require(size and archive.stat().st_size == int(size[1]),
                "Archive size differs")
        data = archive.read_bytes()
        for algorithm, constructor in (("BLAKE2s", hashlib.blake2s),
                                       ("SHA512", hashlib.sha512),
                                       ("SHA256", hashlib.sha256)):
            expected = re.search(r"^" + algorithm + r" \(" + re.escape(release)
                                 + r"\.tar\.xz\) = ([0-9a-f]+)$", info, re.M)
            require(expected and constructor(data).hexdigest() == expected[1],
                    f"Archive {algorithm} differs: {release}")
        size = re.search(r"^Size \(" + re.escape(release)
                         + r"\.tar\.xz\) = ([0-9]+) bytes$", info, re.M)
        require(size and len(data) == int(size[1]), "Archive size differs")
        patches = sorted((path / "patches").glob("patch-*"))
        source_files = {"po/LINGUAS"}
        for patch in patches:
            expected = re.search(r"^SHA1 \(" + re.escape(patch.name)
                                 + r"\) = ([0-9a-f]+)$", info, re.M)
            require(expected and EXPORTER.patch_sha1(patch)
                    == expected[1], f"Patch hash differs: {patch.name}")
            old_paths = re.findall(r"^--- (\S+)\.orig$", patch.read_text(), re.M)
            require(len(old_paths) == 1, "Each source patch has one fixed file")
            source_files.update(old_paths)
        source_files.update({"configure", "src/Makefile.in"} if release.startswith(
            "diffutils") else {"gnulib-tests/localename.c"})
        work = args.work / release
        work.mkdir()
        original = {}
        with tarfile.open(archive) as tar:
            for relative in sorted(source_files):
                require(not PurePosixPath(relative).is_absolute()
                        and ".." not in PurePosixPath(relative).parts,
                        "Unsafe source path")
                member = tar.getmember(release + "/" + relative)
                require(member.isfile() and member.size < 4 * 1024 * 1024,
                        "Source member is not a bounded regular file")
                contents = tar.extractfile(member).read()
                original[relative] = contents
                destination = work / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(contents)
        for patch in patches:
            result = patch_run(args.patch, patch, work)
            require(result.returncode == 0, result.stdout.decode(errors="replace"))
            require(b"offset" not in result.stdout and b"fuzz" not in result.stdout,
                    "Source patch needs an exact refreshed hunk")
            reports.append({"patch": str(patch.relative_to(ROOT)),
                            "exit": result.returncode,
                            "output": result.stdout.decode()})
        expected_configure = original["configure"].decode()
        require(expected_configure.count(GUARD_FROM) == 1, "xargs probe changed")
        expected_configure = expected_configure.replace(GUARD_FROM, GUARD_TO)
        if release.startswith("diffutils"):
            expected_configure, count = re.subn(r"(?m)^(\s*(?:if )?)diff ",
                                               r"\1cmp -s ", expected_configure)
            require(count == 6, "Require all six equality checks")
        else:
            require(b"extern char * getlocalename_l(int, locale_t);"
                    not in original["gnulib-tests/localename.c"],
                    "The removed Solaris patch is still needed")
        require((work / "configure").read_text() == expected_configure,
                "Configure patch changes more than the finite source delta")
        locales = set(original["po/LINGUAS"].decode().split())
        plist = (path / "PLIST").read_text()
        installed = set(re.findall(r"share/locale/([^/]+)/LC_MESSAGES/", plist))
        require(locales == installed, "PLIST must keep all release translations")
        for patch in reversed(patches):
            result = patch_run(args.patch, patch, work, "--reverse")
            require(result.returncode == 0, "Patch reverse failed")
        require(all((work / k).read_bytes() == v for k, v in original.items()),
                "Source patches do not reverse to the exact release")
    # Causal control: a changed old equality command must reject at zero fuzz.
    source = args.work / "diffutils-3.12"
    configure = source / "configure"
    configure.write_bytes(configure.read_bytes().replace(
        b'diff "conftest.out" "conftest.nl"',
        b'changed_source "conftest.out" "conftest.nl"', 1))
    patch = ROOT / "pkgsrc/devel/diffutils/patches/patch-configure"
    refusal = patch_run(args.patch, patch, source, "--dry-run")
    require(refusal.returncode != 0, "Changed source was silently accepted")
    require("--disable-nls" not in (ROOT / "pkgsrc/sysutils/findutils/Makefile").read_text(),
            "The ordinary findutils recipe must retain NLS")
    require("PKG_SUGGESTED_OPTIONS=\tnls" in
            (ROOT / "pkgsrc/devel/diffutils/options.mk").read_text(),
            "The ordinary diffutils recipe must retain default NLS")
    for name in ("diffutils", "findutils"):
        manifest = json.loads((ROOT / "profiles/common-build-tools/bootstrap"
                               / ("gnu-" + name + ".json")).read_text())
        require(manifest["format"] == "emberbsd-native-bootstrap-program"
                and manifest["version"] == 1 and manifest["initial_only"] is True,
                "The finite manifest must keep the existing initial envelope")
        require(manifest["configure_args"] == ["--disable-nls"],
                "Initial configure arguments changed")
        require(all(c.get("command_role", "sh") == "sh"
                    for c in manifest["runtime_cases"]),
                "Only the fixed selected-shell child binding is defined")
    result = {"status": "SOURCE_CHECKS_PASSED", "patches": reports,
              "changed_source_control": {"exit": refusal.returncode,
                                         "output": refusal.stdout.decode()},
              "configure_or_compiler_executed": False}
    (args.work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: five exact reversible patches, release hashes and locales, "
          "six equality checks, two xargs guards, source-change refusal, NLS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diffutils-archive", type=Path, required=True)
    parser.add_argument("--findutils-archive", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    options = parser.parse_args()
    options.archives = [options.diffutils_archive, options.findutils_archive]
    run(options)
