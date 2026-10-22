#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise ICU policy on a complete real payload.
"""Check split ownership and fail-before-prune behavior without a package build."""
import argparse
import os
from pathlib import Path
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sdk-source", "full-stage", "mh-name", "work"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15):
        parser.error("Python 3.15 is required")
    sdk = Path(args.sdk_source).resolve(strict=True)
    sys.path.insert(0, str(sdk / "src"))
    import emberbsd_sdk
    from emberbsd_sdk import inventory, paths, process, stage
    from emberbsd_sdk.errors import CommandError
    if emberbsd_sdk.API_VERSION != 1 or stage.STAGE_PARTITION_API != 1:
        parser.error("SDK API 1 with STAGE_PARTITION_API 1 is required")
    root = Path(__file__).resolve().parents[1]
    recipe = root / "recipes/textproc/icu"
    source = Path(paths.canonical_existing(args.full_stage))
    work = Path(paths.canonical_new(args.work))
    for item in (sdk, source, root):
        paths.reject_overlap(str(work), str(item))
    paths.real_directory(source)
    work.mkdir()
    man_roots = [root for root in ("man", "share/man")
                 if (source / root / "man1/derb.1").is_file()]
    if len(man_roots) != 1:
        parser.error("complete ICU stage must contain one supported man-page layout")
    man_root = man_roots[0]
    manifests = {}
    for part, path in {
            "full": recipe / "PLIST.full-cross",
            "runtime": recipe / "PLIST.runtime",
            "devel": recipe.parent / "icu-devel/PLIST"}.items():
        data = path.read_text(encoding="utf-8").replace("${PKGVERSION}", "78.3")
        data = data.replace("${MH_NAME}", args.mh_name)
        data = "\n".join(
            man_root + name[3:] if name.startswith("man/") else name
            for name in data.splitlines()) + "\n"
        destination = work / (part + ".plist")
        destination.write_text(data, encoding="utf-8")
        manifests[part] = destination
    files = [name for name in manifests["full"].read_text().splitlines()
             if name and not name.startswith("@comment")]

    def copy_stage(label, selected_manifests=manifests):
        destination = work / label
        destination.mkdir()
        selected_files = [
            name for name in selected_manifests["full"].read_text().splitlines()
            if name and not name.startswith("@comment")
        ]
        for name in selected_files:
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            origin = source / name
            if not os.path.lexists(origin) and name.startswith("man/"):
                origin = source / "share" / name
            elif (not os.path.lexists(origin)
                  and name.startswith("share/man/")):
                origin = source / name.removeprefix("share/")
            shutil.copy2(origin, target, follow_symlinks=False)
        return destination

    def run(label, part, payload, lists=manifests, *, success=True, sdk_path=sdk):
        command = [sys.executable, "-B", recipe / "files/select-stage.py",
                   "--sdk-source", sdk_path, part, payload,
                   lists["full"], lists["runtime"], lists["devel"]]
        before = inventory.snapshot_tree(payload)
        try:
            result = process.capture([str(item) for item in command])
            output, errors, status = result.stdout, result.stderr, result.returncode
        except CommandError as error:
            output, errors, status = error.stdout, error.stderr, error.returncode
        (work / (label + ".stdout")).write_bytes(output)
        (work / (label + ".stderr")).write_bytes(errors)
        if success != (status == 0):
            raise ValueError(f"unexpected {label} status {status}; inspect {work}")
        if not success and inventory.snapshot_tree(payload) != before:
            raise ValueError(f"rejected ICU policy changed the stage: {label}")

    runtime = copy_stage("runtime")
    expected = inventory.snapshot_tree(runtime)
    run("runtime", "runtime", runtime)
    sdk_stage = copy_stage("devel")
    run("devel", "devel", sdk_stage)
    # Reassemble the two partitions and compare actual contents and link targets.
    for name in files:
        if os.path.lexists(runtime / name) == os.path.lexists(sdk_stage / name):
            raise ValueError(f"missing or overlapping split payload: {name}")
        if os.path.lexists(runtime / name):
            target = sdk_stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(runtime / name, target, follow_symlinks=False)
    if inventory.snapshot_tree(sdk_stage) != expected:
        raise ValueError("partition union changed the complete payload")

    # The checked-in PLIST uses man/man1. Verify that the selector also accepts
    # that layout when the installed full PLIST has not been relocated by pkgsrc.
    raw_manifests = {}
    for part, path in manifests.items():
        data = "\n".join(
            name.removeprefix("share/")
            if name.startswith("share/man/") else name
            for name in path.read_text(encoding="utf-8").splitlines()) + "\n"
        raw_path = work / (part + "-man.plist")
        raw_path.write_text(data, encoding="utf-8")
        raw_manifests[part] = raw_path
    raw_runtime = copy_stage("raw-man-layout", raw_manifests)
    run("raw-man-layout", "runtime", raw_runtime, raw_manifests)

    rejected = copy_stage("rejected")
    run("unknown-part", "other", rejected, success=False)
    (rejected / "unlisted-file").write_text("unexpected", encoding="utf-8")
    run("unlisted-file", "runtime", rejected, success=False)
    (rejected / "unlisted-file").unlink()
    duplicate = work / "duplicate.plist"
    duplicate.write_text(manifests["runtime"].read_text() + "bin/icuinfo\n")
    run("duplicate", "runtime", rejected,
        dict(manifests, runtime=duplicate), success=False)
    leaked = work / "leaked-generator.plist"
    leaked.write_text(manifests["runtime"].read_text() + "bin/genrb\n")
    run("leaked-generator", "runtime", rejected,
        dict(manifests, runtime=leaked), success=False)
    missing = rejected / "bin/icuinfo"
    missing.unlink()
    run("missing-file", "runtime", rejected, success=False)
    shutil.copy2(source / "bin/icuinfo", missing, follow_symlinks=False)
    # A valid base SDK without the required feature must fail before pruning.
    old_sdk = work / "old-sdk/src/emberbsd_sdk"
    old_sdk.mkdir(parents=True)
    (old_sdk / "__init__.py").write_text("API_VERSION = 1\n")
    (old_sdk / "stage.py").write_text("STAGE_PARTITION_API = 0\n")
    run("missing-feature", "runtime", rejected, success=False,
        sdk_path=old_sdk.parents[1])
    (old_sdk / "stage.py").write_text("STAGE_PARTITION_API = True\n")
    run("boolean-feature", "runtime", rejected, success=False,
        sdk_path=old_sdk.parents[1])
    print(f"PASS: real {len(files)}-file ICU payload partitions, both man layouts, "
          "and seven refusals; payload policy checks do not establish a split target package")


if __name__ == "__main__":
    main()
