#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). ICU package policy for the shared SDK API.
"""Select an exhaustive ICU runtime or development-host SDK partition."""
from pathlib import Path
import os
import shutil
import re
import sys

sys.dont_write_bytecode = True
from sdk_source import exit_error, install_signal_handlers, load_sdk


def manifest(path):
    from emberbsd_sdk.paths import regular_file

    regular_file(path)
    result = set()
    for name in Path(path).read_text(encoding="utf-8").splitlines():
        if not name or re.match(r"^@comment(?: |$)", name):
            continue
        if (re.search(r"[\x00-\x20\x7f]", name)
                or name.startswith(("/", "@")) or name.endswith("/")
                or "${" in name
                or any(part in ("", ".", "..") for part in name.split("/"))):
            raise ValueError(f"unsafe ICU manifest entry: {name}")
        if name in result:
            raise ValueError(f"duplicate ICU manifest entry: {name}")
        result.add(name)
    if not result:
        raise ValueError("empty ICU package manifest")
    return result


def check_policy(full, runtime, devel):
    if runtime & devel or runtime | devel != full:
        raise ValueError("ICU partitions do not exhaust the full manifest")
    # Conversion, inspection and resource dumping are installed user commands.
    # Data generators, link interfaces and build metadata belong to the SDK.
    expected = {"bin/derb", "bin/icuinfo", "bin/uconv",
                "share/icu/79.1/LICENSE"}
    # pkgsrc expands man-page PLIST entries through PKGMANDIR. Accept the
    # standard "man" and "share/man" layouts, but require exactly one path
    # for each runtime command.
    for command in ("derb", "uconv"):
        manpages = {
            f"{root}/man1/{command}.1"
            for root in ("man", "share/man")
        } & full
        if len(manpages) != 1:
            raise ValueError(f"ICU full PLIST requires one {command} manual")
        expected.update(manpages)
    expected.update(name for name in full
                    if re.fullmatch(r"lib/libicu[a-z0-9]+\.so\.79(?:\.1)?", name))
    if not expected <= full or runtime != expected:
        raise ValueError("ICU runtime PLIST differs from the shared-library and user-command policy")
    if not any(name.startswith("lib/libicuuc.so.") for name in runtime):
        raise ValueError("ICU runtime requires its versioned core library")
    return full, runtime, devel


def select(part, stage, *lists):
    from emberbsd_sdk import stage as stage_api

    feature = getattr(stage_api, "STAGE_PARTITION_API", None)
    if (type(feature) is not int or feature != 1
            or not callable(getattr(stage_api, "partition_stage", None))):
        raise ValueError("the selected SDK must provide STAGE_PARTITION_API 1")
    if part not in ("runtime", "devel") or len(lists) != 3:
        raise ValueError("unknown ICU package part or manifest count")
    full, runtime, devel = check_policy(*map(manifest, lists))
    result = stage_api.partition_stage(
        stage, full, {"runtime": runtime, "devel": devel}, part,
        dependencies={"devel": ["runtime"]})
    print(f"PASS: complete ICU stage selects {part}: "
          f"{len(result['kept_files'])}/{result['complete_files']} files")



def copy_complete(source, destination, lists, *, allow_empty=False):
    from emberbsd_sdk import inventory, paths

    full, runtime, devel = check_policy(*map(manifest, lists))
    if not callable(getattr(inventory, "transfer_inventory_equal", None)):
        raise ValueError("the selected SDK must provide inventory transfer validation")
    source = paths.path_string(source)
    destination = paths.path_string(destination)
    if paths.canonical_existing(source) != source or paths.canonical_new(destination) != destination:
        raise ValueError("ICU stages require normalized paths with real ancestors")
    paths.real_directory(source)
    paths.reject_overlap(source, destination)
    existing = os.path.lexists(destination)
    if existing:
        if not allow_empty:
            raise ValueError("shared-stage destination already exists")
        paths.real_directory(destination)
        if os.listdir(destination):
            raise ValueError("ICU package destination is not empty")
    before = inventory.snapshot_tree(source)
    if {name for name, row in before.items() if row['kind'] != 'directory'} != full:
        raise ValueError("actual ICU complete stage differs from its manifest")
    parent = Path(destination).parent
    parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(source, destination, symlinks=True, dirs_exist_ok=existing)
        copied = inventory.snapshot_tree(destination)
        if (not inventory.transfer_inventory_equal(before, copied)
                or inventory.snapshot_tree(source) != before):
            raise ValueError("ICU stage changed or differs during handoff")
    except Exception:
        if os.path.isdir(destination) and not os.path.islink(destination):
            shutil.rmtree(destination)
        raise
    return destination

def main():
    install_signal_handlers()
    if sys.version_info[:2] != (3, 15):
        raise ValueError("ICU stage selection requires Python 3.15")
    _, args = load_sdk()
    if len(args) == 5 and args[0] in ("runtime", "devel"):
        select(*args)
    elif len(args) == 6 and args[0] == "handoff-runtime":
        _, source, full, runtime, devel, shared = args
        copy_complete(source, shared, (full, runtime, devel))
        try:
            select("runtime", source, full, runtime, devel)
        except Exception:
            shutil.rmtree(shared)
            raise
    elif len(args) == 6 and args[0] == "copy-devel":
        _, shared, destination, full, runtime, devel = args
        copy_complete(shared, destination, (full, runtime, devel), allow_empty=True)
        try:
            select("devel", destination, full, runtime, devel)
        except Exception:
            shutil.rmtree(destination)
            raise
    else:
        raise ValueError("usage: select-stage.py --sdk-source SOURCE runtime|devel|handoff-runtime|copy-devel ...")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        exit_error(error)
