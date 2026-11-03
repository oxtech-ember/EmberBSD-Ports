#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Audit the ordered BSD overlay against Electron's committed source graph."""

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile

spec = importlib.util.spec_from_file_location(
    "electron_upstream", Path(__file__).with_name("apply-upstream-patches.py"))
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)
require = upstream.require
DATA = Path(__file__).with_name("bsd-overlay")


def validate_common_source(name, target, content, entry):
    require(target.startswith("v8/") and entry.get("provider") == "pkgsrc/lang/v8",
            "unsupported common source overlay: " + name)
    require(entry.get("mapping") and hashlib.sha256(content).hexdigest() == entry.get("patch_sha256"),
            "common source donor patch differs: " + name)


def relative(name):
    path = PurePosixPath(name)
    require(name and path.parts and not path.is_absolute() and str(path) == name and
            not any(part.casefold() in ("", ".", "..", ".git") for part in path.parts) and
            not any(character.isspace() for character in name) and "\\" not in name,
            f"unsafe overlay path: {name!r}")
    return path


def git_bytes(git, root, *args, data=None):
    env = os.environ.copy()
    env.pop("GIT_INDEX_FILE", None)
    result = subprocess.run([str(git), "-C", str(root), *args], input=data,
                            env=env, capture_output=True)
    require(result.returncode == 0, f"git {args[0]} failed: {result.stderr.decode().strip()}")
    return result.stdout


def files_at(git, root, revision, paths, recursive=False):
    """Read regular blobs from the specified Git tree, never the work tree."""
    require(re.fullmatch(r"[0-9a-f]{40}", revision), "source revision must be a full Git commit")
    argv = ["ls-tree", "-z", "--full-tree"] + (["-r"] if recursive else [])
    entries = git_bytes(git, root, *argv, revision, "--", *paths)
    rows = []
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        info, name = entry.split(b"\t", 1)
        mode, kind, oid = info.decode().split()
        name = name.decode()
        relative(name)
        require(kind == "blob" and mode in ("100644", "100755"),
                f"overlay input is not a regular source file: {name}")
        rows.append((name, mode, oid))
    query = "".join(oid + "\n" for _, _, oid in rows).encode()
    blobs = io.BytesIO(git_bytes(git, root, "cat-file", "--batch", data=query))
    output = {}
    for name, mode, oid in rows:
        header = blobs.readline().decode().split()
        require(len(header) == 3 and header[:2] == [oid, "blob"], "unexpected Git blob response")
        size = int(header[2])
        content = blobs.read(size)
        require(len(content) == size and blobs.read(1) == b"\n", "incomplete Git blob response")
        require(hashlib.sha1(b"blob " + str(size).encode() + b"\0" + content).hexdigest() == oid,
                f"Git blob checksum differs: {name}")
        output[name] = (content, mode)
    require(not blobs.read(), "unexpected trailing Git blob response")
    return output


def patch_target(content):
    lines = content.decode().splitlines()
    headers = [(line[4:].split()[0], lines[index + 1][4:].split()[0])
               for index, line in enumerate(lines[:-1])
               if line.startswith("--- ") and lines[index + 1].startswith("+++ ")]
    require(len(headers) == 1, "each baseline patch must affect exactly one regular file")
    old, new = headers[0]
    relative(old)
    relative(new)
    require(old.removesuffix(".orig") == new, f"unexpected patch file pair: {old}, {new}")
    return new


def baseline(git, pkgsrc, manifest):
    prefix = "www/chromium/"
    blobs = files_at(git, pkgsrc, manifest["pkgsrc_revision"],
                     [prefix + "patches", prefix + "distinfo"], recursive=True)
    checks = {}
    for line in blobs[prefix + "distinfo"][0].decode().splitlines():
        match = re.fullmatch(r"SHA1 \((patch-[^)]*)\) = ([0-9a-f]{40})", line)
        if match:
            require(match[1] not in checks, "duplicate patch checksum")
            checks[match[1]] = match[2]
    patches = {name.removeprefix(prefix + "patches/"): value[0]
               for name, value in blobs.items() if name.startswith(prefix + "patches/patch-")}
    require(len(patches) == manifest["patch_count"] and patches.keys() == checks.keys(),
            "baseline patch set differs from its complete distinfo list")
    for name, content in patches.items():
        require(relative(name).name == name, "baseline patch must be a plain filename")
        # Match pkgsrc mk/checksum/checksum.awk's exclusion of NetBSD Id lines.
        filtered = b"".join(line for line in content.splitlines(keepends=True) if b"$NetBSD" not in line)
        require(hashlib.sha1(filtered).hexdigest() == checks[name], f"patch checksum differs: {name}")
        patch_target(content)
    return patches


def overlay_files(archive, manifest):
    with archive.open("rb") as source:
        data = source.read(2 * 1024 * 1024 + 1)
    require(len(data) <= 2 * 1024 * 1024, "chromium-nb gzip exceeds its size bound")
    require(hashlib.sha512(data).hexdigest() == manifest["archive_sha512"],
            "chromium-nb archive checksum differs")
    # Bound expansion before tarfile parses extended metadata.
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as zipped:
        raw = zipped.read(2 * 1024 * 1024 + 1)
    require(len(raw) <= 2 * 1024 * 1024, "chromium-nb tar exceeds its size bound")
    files, seen, ancestors = {}, set(), {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
        for member in tar:
            name = member.name.rstrip("/")
            path = relative(name)
            require(path.parts[0] == manifest["archive_root"], "unexpected chromium-nb archive root")
            require(name.casefold() not in seen, f"duplicate or case-colliding archive path: {name}")
            seen.add(name.casefold())
            for index in range(1, len(path.parts) + 1):
                ancestor = "/".join(path.parts[:index])
                require(ancestors.setdefault(ancestor.casefold(), ancestor) == ancestor,
                        f"case-colliding archive parent: {name}")
            require(member.isdir() or member.isfile(), f"unsupported chromium-nb member: {name}")
            if member.isfile():
                target = str(PurePosixPath(*path.parts[1:]))
                relative(target)
                require(member.size <= 1024 * 1024, "chromium-nb member exceeds its size bound")
                files[target] = tar.extractfile(member).read()
    return files


def committed_sources(workspace, git, targets):
    inputs = workspace / "source-inputs"
    actual = json.loads((inputs / "git-revisions.json").read_text())
    declared = json.loads((inputs / "declared-dependencies.json").read_text())
    upstream.sync.check_inventory(declared, actual)
    record = json.loads((inputs / "upstream-patches.json").read_text())
    require(record["applied"].get("src", {}).get("base") == upstream.source.CHROMIUM_REVISION,
            "Chromium upstream patch base differs from the recipe pin")
    groups, revisions = {}, {}
    for target in targets:
        name = "src/" + str(relative(target))
        owner = max((repo for repo in actual if name.startswith(repo + "/")), key=len)
        groups.setdefault(owner, []).append(name[len(owner) + 1:])
    output = {}
    for owner, names in sorted(groups.items()):
        root = workspace / owner
        require(root.resolve().is_relative_to(workspace) and not root.is_symlink(),
                f"source repository escapes workspace: {owner}")
        require(git_bytes(git, root, "rev-parse", "--show-toplevel").decode().strip() == str(root),
                f"source input is not its own repository: {owner}")
        revision = actual[owner]["rev"]
        if owner in record["applied"]:
            entry = record["applied"][owner]
            require(entry["base"] == revision, f"upstream patch base differs: {owner}")
            revision = entry["patched"]
        require(git_bytes(git, root, "rev-parse", "HEAD").decode().strip() == revision,
                f"source repository HEAD differs: {owner}")
        revisions[owner] = revision
        for name, (content, mode) in files_at(git, root, revision, names).items():
            output[(PurePosixPath(owner) / name).relative_to("src").as_posix()] = content
    return output, revisions


def run_patch(patch, directory, filename, strip, log):
    argv = [str(patch), "-f", "-N", "-F", "0", "-E", f"-p{strip}",
            "-d", str(directory), "-i", str(filename)]
    result = subprocess.run(argv, capture_output=True, text=True)
    log.write_text(result.stdout + result.stderr)
    require(result.returncode == 0, f"zero-fuzz patch failed: {filename.name}; see {log}")


def audit(workspace, pkgsrc, archive, destination, git, patch):
    workspace = workspace.resolve(strict=True)
    pkgsrc = pkgsrc.resolve(strict=True)
    destination = destination.absolute()
    require(not destination.exists() and not destination.is_symlink(), "audit destination must be new")
    destination = destination.parent.resolve(strict=True) / destination.name
    require(not destination.is_relative_to(workspace) and not destination.is_relative_to(pkgsrc),
            "audit destination must be outside source repositories")
    for name, executable in (("git", git), ("patch", patch)):
        require(executable.is_absolute() and executable.is_file() and os.access(executable, os.X_OK),
                f"--{name} must name an absolute executable")
    manifest = json.loads((DATA / "manifest.json").read_text())
    patches = baseline(git, pkgsrc, manifest)
    overlay = overlay_files(archive, manifest)
    destination.mkdir()
    series = destination / "series"
    series.mkdir()
    logs = destination / "logs"
    logs.mkdir()
    for name, content in patches.items():
        (series / name).write_bytes(content)
    run_patch(patch, series, DATA / "adaptations.patch", 1, logs / "adaptations.log")
    require({p.name for p in series.iterdir() if not p.name.endswith(".orig")} == set(patches),
            "adaptations changed the baseline patch set")
    changed = {name for name, content in patches.items() if (series / name).read_bytes() != content}
    require(changed == {entry["patch"] for entry in manifest["adapted"]},
            "adaptations differ from their declared patch set")
    targets = {name: patch_target((series / name).read_bytes()) for name in sorted(patches)}
    require(len({name.casefold() for name in targets.values()}) == len(targets),
            "duplicate or case-colliding patch target")
    external = manifest["external_host_tools"]
    superseded = manifest["superseded"]
    common_sources = manifest.get("common_sources", {})
    require(set(common_sources) == {name for name, target in targets.items() if target.startswith("v8/")},
            "common V8 overlay inventory differs from the archive")
    require(set(external) | set(superseded) | set(common_sources) <= set(patches) and
            not (set(external) & set(superseded) or set(external) & set(common_sources) or
                 set(superseded) & set(common_sources)),
            "invalid overlay classification")
    for name, entry in [(entry["patch"], entry) for entry in manifest["adapted"]] + list(superseded.items()) + list(common_sources.items()):
        require(targets.get(name) == entry["target"], f"classified patch target differs: {name}")
    sources, revisions = committed_sources(workspace, git, list(targets.values()))
    require(not set(sources) & set(overlay), "chromium-nb overwrites a committed source file")
    sources.update(overlay)
    for entry in [*manifest["adapted"], *superseded.values()]:
        require(entry["target"] in sources and
                hashlib.sha256(sources[entry["target"]]).hexdigest() == entry["source_sha256"],
                f"adapted or superseded source differs: {entry['target']}")
    fixture = destination / "files"
    fixture.mkdir()
    for name, content in sources.items():
        target = fixture / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    rows = []
    for name, target in targets.items():
        row = {"patch": name, "target": target,
               "sha256": hashlib.sha256((series / name).read_bytes()).hexdigest()}
        if name in external:
            require(target not in sources, f"external host source unexpectedly exists: {target}")
            row.update(status="external-host-tool", **external[name])
        elif name in common_sources:
            validate_common_source(name, target, (series / name).read_bytes(), common_sources[name])
            row.update(status="common-source", provider=common_sources[name]["provider"],
                       mapping=common_sources[name]["mapping"])
        elif name in superseded:
            row.update(status="superseded", reason=superseded[name]["reason"])
        else:
            creates = bool(re.search(rb"^@@ -0,0 \+1(?:,\d+)? @@",
                                     (series / name).read_bytes(), re.MULTILINE))
            require((target not in sources) if creates else (target in sources),
                    f"selected overlay source has unexpected existence: {target}")
            run_patch(patch, fixture, series / name, 0, logs / (name + ".log"))
            row["status"] = "applied"
        rows.append(row)
    result = {"scope": "Committed source fixture, ordered zero-fuzz BSD patches; no build or production mutation",
              "pkgsrc_revision": manifest["pkgsrc_revision"], "source_revisions": revisions,
              "archive_sha512": manifest["archive_sha512"], "rows": rows}
    temporary = destination / ".audit.json"
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary.replace(destination / "audit.json")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("workspace", "pkgsrc", "archive", "destination", "git", "patch"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(**vars(args))
    except (ValueError, OSError, KeyError, tarfile.TarError) as exc:
        parser.exit(1, f"BSD overlay audit failed: {exc}\n")
    counts = {status: sum(row["status"] == status for row in result["rows"])
              for status in ("applied", "superseded", "external-host-tool", "common-source")}
    print(json.dumps(counts, sort_keys=True))
    print("External host inputs, other Electron adaptations and target compilation remain separate work.")


if __name__ == "__main__":
    main()
