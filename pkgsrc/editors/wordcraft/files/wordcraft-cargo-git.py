# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Expose the Git workspaces extracted by pkgsrc to Cargo's offline resolver."""
import argparse
import json
import re
import tomllib
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit


def manifests(root):
    # craft-libs carries the patched krilla under vendor/. egui uses crates/.
    paths = set()
    for pattern in ("Cargo.toml", "*/Cargo.toml", "crates/*/Cargo.toml", "vendor/*/Cargo.toml"):
        paths.update(root.glob(pattern))
    for path in sorted(paths):
        data = tomllib.loads(path.read_text())
        if "package" in data:
            yield path, data


def link_member(vendor, path, data, root, version):
    package = data["package"]
    name = package["name"]
    # Cargo sees a directory source through the link below. Give its workspace
    # members their real parent so inheritance and relative dependencies work.
    if "workspace" not in data and "workspace" not in package:
        for parent in (path.parent, *path.parent.parents):
            manifest = parent / "Cargo.toml"
            if manifest.is_file() and "workspace" in tomllib.loads(manifest.read_text()):
                text = path.read_text()
                path.write_text(text.replace("[package]", "[package]\nworkspace = " + json.dumps(str(parent)), 1))
                break
            if parent == root:
                break
    # distinfo verified the complete archive, as for pkgsrc registry crates.
    (path.parent / ".cargo-checksum.json").write_text('{"files":{},"package":null}\n')
    entry = vendor / f"{name}-{version}"
    if not entry.is_symlink():
        entry.symlink_to(path.parent, target_is_directory=True)
    elif entry.resolve() != path.parent:
        raise ValueError(f"{entry} already names a different package")


def configure(lockfile, work, config):
    lock = tomllib.loads(lockfile.read_text())
    sources = defaultdict(dict)
    for package in lock["package"] + lock.get("patch", {}).get("unused", []):
        source = package.get("source", "")
        if source.startswith("git+"):
            sources[source][package["name"]] = package["version"]

    tables = []
    for source, packages in sorted(sources.items()):
        # All Git inputs in this release are HTTPS repositories pinned by rev.
        match = re.fullmatch(r"git\+(https://github\.com/[\w.-]+/[\w.-]+)\?rev=([a-f0-9]{40})#\2", source)
        if not match:
            raise ValueError(f"expected a pinned Git source in Cargo.lock: {source}")
        url, rev = match.groups()
        repo = Path(urlsplit(url).path).name.removesuffix(".git")
        root = work / f"{repo}-{rev}"
        vendor = work / "wordcraft-git" / root.name
        vendor.mkdir(parents=True, exist_ok=True)
        remaining = dict(packages)
        for path, data in manifests(root):
            name = data["package"]["name"]
            if name in remaining:
                link_member(vendor, path, data, root, remaining.pop(name))
        if remaining:
            raise ValueError(f"{root}: missing locked crates {', '.join(remaining)}")
        alias = json.dumps(root.name)
        tables.extend([f"[source.{json.dumps(source.split('#')[0])}]",
                       "git = " + json.dumps(url), "rev = " + json.dumps(rev), "replace-with = " + alias,
                       f"[source.{alias}]", "directory = " + json.dumps(str(vendor)), ""])
    config.write_text("\n".join(tables))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lockfile", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    configure(args.lockfile, args.work.resolve(), args.config)
