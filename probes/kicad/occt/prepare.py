#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), pinned OCCT source preparation.
"""Prepare the complete source with an explicitly selected SDK host API."""
import argparse
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-source", required=True, type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("new_source", type=Path)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15):
        raise SystemExit("Use the qualified native Python 3.15 interpreter.")
    sdk = args.sdk_source.resolve(strict=True)
    sys.path.insert(0, str(sdk / "src"))
    import emberbsd_sdk
    if emberbsd_sdk.API_VERSION != 1:
        raise SystemExit("SDK host API 1 is required.")
    if Path(emberbsd_sdk.__file__).resolve().parent != sdk / "src/emberbsd_sdk":
        raise SystemExit("The SDK import did not use the selected source.")
    from emberbsd_sdk.errors import CommandError, SDKError
    from emberbsd_sdk.jsonio import loads_json, write_json
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.paths import canonical_new, reject_overlap
    from emberbsd_sdk.process import capture
    from emberbsd_sdk.provenance import git_source
    try:
        owner = Path(__file__).resolve().parent
        archive = args.archive.resolve(strict=True)
        destination = Path(canonical_new(args.new_source))
        if not args.new_source.is_absolute() or args.new_source.exists() or args.new_source.is_symlink():
            raise SDKError("Use a new absolute source destination.")
        reject_overlap(str(destination), str(owner))
        reject_overlap(str(destination), str(archive))
        reject_overlap(str(destination), str(sdk))
        metadata = loads_json((owner / "source.json").read_bytes())
        if sha256_file(archive) != metadata["sha256"]:
            raise SDKError("Archive hash mismatch.")
        patches = []
        for entry in metadata["patches"]:
            relative = Path(entry["path"])
            if not relative.parts or relative.is_absolute() or ".." in relative.parts or relative.parts[0] != "patches":
                raise SDKError("Unexpected patch path.")
            patch = (owner / relative).resolve(strict=True)
            if patch.parent != owner / "patches" or sha256_file(patch) != entry["sha256"]:
                raise SDKError("Patch origin or hash mismatch.")
            patches.append(patch)
        if len(set(patches)) != len(patches):
            raise SDKError("Duplicate patch.")
        environment = dict(os.environ)
        sdk_provenance = git_source(str(sdk), env=environment)
        destination.mkdir(parents=True)
        commands = [["tar", "-xzf", str(archive), "--strip-components=1", "-C", str(destination)]]
        commands += [["patch", "--batch", "--fuzz=0", "-p1", "-d", str(destination), "-i", str(patch)] for patch in patches]
        receipts = []
        for index, command in enumerate(commands):
            try:
                result = capture(command, env=environment)
                code, stdout, stderr = 0, result.stdout, result.stderr
            except CommandError as error:
                code, stdout, stderr = error.returncode, error.stdout, error.stderr
            (destination / f"emberbsd-prepare-{index}.stdout").write_bytes(stdout)
            (destination / f"emberbsd-prepare-{index}.stderr").write_bytes(stderr)
            receipts.append(dict(args=command, status=code))
            write_json(str(destination / "emberbsd-prepare-commands.json"), receipts, exclusive=False)
            if code:
                raise SDKError(f"Source preparation failed with status {code}; retain {destination}.")
        write_json(str(destination / "emberbsd-source.json"), metadata)
        write_json(str(destination / "emberbsd-host.json"), dict(
            sdk_source=sdk_provenance, sdk_api=1,
            python=str(Path(sys.executable).resolve()), python_version=sys.version,
            helper_sha256=sha256_file(Path(__file__).resolve()), scope="Source preparation only; no build or package acceptance."))
        print(f"Prepared OCCT {metadata['version']}: {destination}")
    except (SDKError, OSError, KeyError, TypeError, ValueError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    main()
