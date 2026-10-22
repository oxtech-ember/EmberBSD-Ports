#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real alternate-root package deletion regression.
"""Check actual deinstall.mk rules with real native pkgtools and isolated data packages."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    repo = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pkgtools", type=Path, help="Directory with native pkg_add, pkg_delete, pkg_info, pkg_admin and pkg_create")
    parser.add_argument("work", type=Path)
    parser.add_argument("--bmake", required=True, type=Path)
    parser.add_argument("--pkgsrc", type=Path, default=repo / "upstream/pkgsrc")
    parser.add_argument("--patch", type=Path,
                        default=repo / "profiles/common-build-tools/patches/pkgsrc-cross-packages.patch")
    args = parser.parse_args()
    for path in (args.pkgtools, args.work, args.bmake, args.pkgsrc, args.patch):
        require(path.is_absolute() and re.fullmatch(r"[A-Za-z0-9_./-]+", str(path)), "Use absolute paths without shell metacharacters")
    require(not os.path.lexists(args.work), "Use a new work directory")
    args.work.mkdir(parents=True)
    work = args.work.resolve(strict=True)
    commands = []

    def run(name, command, *, ok=True):
        argv = [str(item) for item in command]
        result = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        (work / (name + ".log")).write_text(result.stdout)
        commands.append({"name": name, "argv": argv, "returncode": result.returncode})
        if ok:
            require(result.returncode == 0, name + ": " + result.stdout)
        return result

    tools = {name: (args.pkgtools / name).resolve(strict=True)
             for name in ("pkg_add", "pkg_delete", "pkg_info", "pkg_admin", "pkg_create")}
    for name, path in tools.items():
        run(name + "-version", [path, "-V"])
    source = args.pkgsrc / "mk/pkgformat/pkg/deinstall.mk"
    original = source.read_text()
    patch_text = args.patch.read_text()
    start = patch_text.index("--- a/mk/pkgformat/pkg/deinstall.mk\n")
    end = patch_text.find("\n--- a/", start + 1)
    delta = patch_text[start:] if end == -1 else patch_text[start:end + 1]
    (work / "deinstall.patch").write_text(delta)
    for mode in ("before", "after"):
        directory = work / mode / "mk/pkgformat/pkg"
        directory.mkdir(parents=True)
        (directory / "deinstall.mk").write_text(original)
    applied = run("patch", ["patch", "-d", work / "after", "-p1", "-F0", "-i", work / "deinstall.patch"])
    require("fuzz" not in applied.stdout and "offset" not in applied.stdout, "The deinstall patch did not apply exactly")
    repaired = (work / "after/mk/pkgformat/pkg/deinstall.mk").read_text()
    require(repaired.replace("-K ${PKG_DBDIR:Q} -P ${_CROSS_DESTDIR:Q} -p ${PREFIX:Q}",
                             "-p ${_CROSS_DESTDIR}${PREFIX}") == original,
            "The patch changed native or dependency deinstall behavior")
    payload = work / "payload"
    (payload / "share/ember-deinstall/empty").mkdir(parents=True)
    (work / "comment").write_text("Isolated cross deinstall fixture\n")
    (work / "description").write_text("Data only. No target scripts or executable files.\n")
    (work / "build-info").write_text("OPSYS=NetBSD\nMACHINE_ARCH=aarch64\nOS_VERSION=11.0\nPKGTOOLS_VERSION=20260227\n")
    for version in ("1.0", "2.0", "hold-1.0"):
        leaf = "hold" if version.startswith("hold") else "version"
        (payload / "share/ember-deinstall" / leaf).write_text(version + "\n")
        plist = "@name ember-deinstall-" + version + "\n"
        if version.startswith("hold"):
            plist += "@pkgdep ember-deinstall-1.0\n"
        plist += "share/ember-deinstall/" + leaf + "\n"
        if not version.startswith("hold"):
            plist += "@pkgdir share/ember-deinstall/empty\n"
        (work / "plist").write_text(plist)
        run("create-" + version, [tools["pkg_create"], "-p", payload, "-I", "/usr/pkg", "-f", work / "plist",
            "-c", work / "comment", "-d", work / "description", "-B", work / "build-info", work / (version + ".tgz")])

    def setup(label, mode, cross):
        directory = work / label
        directory.mkdir()
        root = directory / "root"
        root.mkdir()
        prefix = "/usr/pkg" if cross else str(directory / "prefix")
        db_logical = "/usr/pkg/pkgdb" if cross else str(directory / "pkgdb")
        db = Path(str(root) + db_logical) if cross else Path(db_logical)
        physical_prefix = Path(str(root) + prefix) if cross else Path(prefix)
        makefile = directory / "Makefile"
        makefile.write_text("\n".join([
            "USE_CROSS_COMPILE=" + ("yes" if cross else "no"),
            "_CROSS_DESTDIR=" + (str(root) if cross else ""), "PREFIX=" + prefix,
            "PKG_DBDIR=" + db_logical, "_PKG_DBDIR=${_CROSS_DESTDIR}${PKG_DBDIR}",
            "PKG_DELETE=" + str(tools["pkg_delete"]) + " -K ${_PKG_DBDIR}",
            "PKG_INFO=" + str(tools["pkg_info"]) + " -K ${_PKG_DBDIR}",
            "_PKG_BEST_EXISTS=${PKG_INFO} -E", "PKGWILDCARD=ember-deinstall-[0-9]*",
            "PKGTOOLS_ENV=", "RUN=", "TEST=test", "TRUE=true", "ECHO=echo", "SETENV=env",
            '.include "' + str(work / mode / "mk/pkgformat/pkg/deinstall.mk") + '"', ""]))
        add_args = [tools["pkg_add"], "-m", "NetBSD/aarch64 11.0", "-K", db_logical]
        if cross:
            add_args += ["-P", root]
        add_args += ["-p", prefix]
        return directory, db, physical_prefix, add_args

    def deinstall(label, directory, version):
        return run(label, [args.bmake, "-C", directory, "PKGNAME=ember-deinstall-" + version, "_pkgformat-deinstall"])

    def dump(label, db):
        return run(label, [tools["pkg_admin"], "-K", db, "dump"]).stdout

    def absent_record(label, db, version):
        require(not (db / ("ember-deinstall-" + version)).exists(), "Package record remains")
        require(run(label, [tools["pkg_info"], "-K", db, "-e", "ember-deinstall-" + version], ok=False).returncode != 0,
                "pkg_info still reports the deleted package")

    for mode in ("before", "after"):
        directory, db, prefix, add = setup("cross-" + mode, mode, True)
        run(mode + "-install-1", [*add, work / "1.0.tgz"])
        require("file: /usr/pkg/share/ember-deinstall/version pkg: ember-deinstall-1.0" in dump(mode + "-owner-1", db),
                "Initial owner is not a logical target path")
        deinstall(mode + "-delete-1", directory, "1.0")
        require(not (prefix / "share/ember-deinstall/version").exists(), "Payload remains after deinstall")
        absent_record(mode + "-absent-1", db, "1.0")
        owners = dump(mode + "-deleted-owners", db)
        replacement = run(mode + "-install-2", [*add, work / "2.0.tgz"], ok=False)
        if mode == "before":
            require("file: /usr/pkg/share/ember-deinstall/version pkg: ember-deinstall-1.0" in owners,
                    "The baseline did not leave stale logical ownership")
            require(replacement.returncode != 0 and "conflicting PLIST with ember-deinstall-1.0" in replacement.stdout,
                    "The baseline did not reproduce the new package conflict")
            require(not (db / "ember-deinstall-2.0").exists(), "Failed baseline installation registered a package")
        else:
            require("ember-deinstall-1.0" not in owners and replacement.returncode == 0, "Repaired deinstall left a stale owner")
            require((prefix / "share/ember-deinstall/version").read_text() == "2.0\n", "Replacement payload differs")
            require("file: /usr/pkg/share/ember-deinstall/version pkg: ember-deinstall-2.0" in dump("after-owner-2", db),
                    "Replacement owner is not a logical target path")
            deinstall("after-delete-2", directory, "2.0")
            absent_record("after-absent-2", db, "2.0")
            require("ember-deinstall" not in dump("after-empty", db), "Final target ownership remains")
    # Native commands keep their original flags and remove the same real packages.
    native_flags = {}
    for mode in ("before", "after"):
        directory, db, prefix, add = setup("native-" + mode, mode, False)
        native_flags[mode] = []
        for depends in ("no", "yes", "all"):
            flags = run(mode + "-native-flags-" + depends,
                        [args.bmake, "-C", directory, "DEINSTALLDEPENDS=" + depends, "-V", "${_PKG_ARGS_DEINSTALL}"]).stdout
            native_flags[mode].append(shlex.split(flags))
        run(mode + "-native-install", [*add, work / "1.0.tgz"])
        deinstall(mode + "-native-delete", directory, "1.0")
        absent_record(mode + "-native-absent", db, "1.0")
        require(not (prefix / "share/ember-deinstall/version").exists() and "ember-deinstall" not in dump(mode + "-native-empty", db),
                "Native deletion left payload or ownership")
    require(native_flags["before"] == native_flags["after"] == [[], ["-r", "-R"], ["-r"]], "Native dependency flags changed")
    directory, db, prefix, add = setup("dependent", "after", True)
    run("dependent-install", [*add, work / "1.0.tgz", work / "hold-1.0.tgz"])
    deinstall("dependency-protection", directory, "1.0")
    require((db / "ember-deinstall-1.0").is_dir() and (prefix / "share/ember-deinstall/version").is_file()
            and "file: /usr/pkg/share/ember-deinstall/version pkg: ember-deinstall-1.0" in dump("protected-owner", db),
            "A required package was deleted without permission")
    deinstall("delete-dependent", directory, "hold-1.0")
    deinstall("delete-unrequired", directory, "1.0")
    require("ember-deinstall" not in dump("dependent-empty", db), "Dependency removal left ownership")
    receipt = {"status": "PASS", "scope": "Actual deinstall.mk with isolated make variables and real native package tools. Data-only target metadata; no shared sysroot or VM is used. No force or ownership-check override.",
               "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "patch_sha256": hashlib.sha256(args.patch.read_bytes()).hexdigest(),
               "tools": {name: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for name, path in tools.items()},
               "native_flags": native_flags, "commands": commands}
    (work / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("PASS: baseline stale ownership blocks replacement; fixed target and unchanged native deletion remove payload, records and owners; dependency protection remains active")


if __name__ == "__main__":
    main()
