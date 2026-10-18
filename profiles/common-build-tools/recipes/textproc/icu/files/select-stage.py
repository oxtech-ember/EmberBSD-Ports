#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). ICU package policy for the shared SDK API.
"""Select an exhaustive ICU runtime or development-host SDK partition."""
from pathlib import Path
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


def select(part, stage, *lists):
    from emberbsd_sdk import stage as stage_api

    feature = getattr(stage_api, "STAGE_PARTITION_API", None)
    if (type(feature) is not int or feature != 1
            or not callable(getattr(stage_api, "partition_stage", None))):
        raise ValueError("the selected SDK must provide STAGE_PARTITION_API 1")
    if part not in ("runtime", "devel") or len(lists) != 3:
        raise ValueError("unknown ICU package part or manifest count")
    full, runtime, devel = map(manifest, lists)
    # Conversion, inspection and resource dumping are installed user commands.
    # Data generators, link interfaces and build metadata belong to the SDK.
    expected = {
        "bin/derb", "bin/icuinfo", "bin/uconv",
        "man/man1/derb.1", "man/man1/uconv.1",
        "share/icu/78.3/LICENSE",
    }
    expected.update(name for name in full
                    if re.fullmatch(r"lib/libicu[a-z0-9]+\.so\.78(?:\.3)?", name))
    if not expected <= full or runtime != expected:
        raise ValueError("ICU runtime PLIST differs from the shared-library and user-command policy")
    if not any(name.startswith("lib/libicuuc.so.") for name in runtime):
        raise ValueError("ICU runtime requires its versioned core library")
    result = stage_api.partition_stage(
        stage, full, {"runtime": runtime, "devel": devel}, part,
        dependencies={"devel": ["runtime"]})
    print(f"PASS: complete ICU stage selects {part}: "
          f"{len(result['kept_files'])}/{result['complete_files']} files")


def main():
    install_signal_handlers()
    if sys.version_info[:2] != (3, 15):
        raise ValueError("ICU stage selection requires Python 3.15")
    _, args = load_sdk()
    if len(args) != 5:
        raise ValueError("usage: select-stage.py --sdk-source SOURCE "
                         "runtime|devel STAGE FULL_PLIST RUNTIME_PLIST DEVEL_PLIST")
    select(*args)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        exit_error(error)
