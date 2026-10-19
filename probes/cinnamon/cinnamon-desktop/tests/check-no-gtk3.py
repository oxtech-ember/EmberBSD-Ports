#!/usr/bin/env python3
"""Reject GTK 3 dependencies in the Cinnamon Desktop package and build metadata."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import json
import re
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

FORBIDDEN = re.compile(
    r"gtk\+-3\.0|gtk3\+?|gtk-3(?:\.0)?|libgtk-3(?:\.so)?|"
    r"gdk-3(?:\.0)?|libgdk-3(?:\.so)?|GdkPixbuf-2\.0",
    re.IGNORECASE,
)
EXPECTED_GIRS = {
    "share/gir-1.0/CDesktopEnums-3.0.gir": "CDesktopEnums-3.0",
    "share/gir-1.0/CinnamonDesktop-3.0.gir": "CinnamonDesktop-3.0",
    "share/gir-1.0/Cvc-1.0.gir": "Cvc-1.0",
}

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--package", required=True, type=Path)
parser.add_argument("--pkg-config-log", required=True, type=Path)
parser.add_argument("--meson-setup-log", required=True, type=Path)
parser.add_argument("--meson-dependencies", required=True, type=Path)
args = parser.parse_args()
assert all(path.is_absolute() and path.is_file() for path in vars(args).values())

for label, path in (
    ("pkg-config log", args.pkg_config_log),
    ("Meson setup log", args.meson_setup_log),
):
    text = path.read_text(errors="replace")
    assert not FORBIDDEN.search(text), f"GTK 3 dependency found in {label}"

dependencies = json.loads(args.meson_dependencies.read_text())
names = {entry.get("name", "") for entry in dependencies}
assert not any(FORBIDDEN.search(name) for name in names), names

with tarfile.open(args.package, "r:gz") as package:
    members = set(package.getnames())
    package_contents = package.extractfile("+CONTENTS")
    assert package_contents is not None, "package is missing +CONTENTS"
    assert not FORBIDDEN.search(package_contents.read().decode(errors="replace")), (
        "GTK 3 dependency found in package requirements"
    )

    for path, typelib_stem in EXPECTED_GIRS.items():
        assert path in members, f"missing package GIR: {path}"
        typelib = path.replace("share/gir-1.0/", "lib/girepository-1.0/").replace(
            ".gir", ".typelib"
        )
        assert typelib in members, f"missing package typelib: {typelib}"
        root = ET.fromstring(package.extractfile(path).read())
        namespace = root.find("{*}namespace")
        assert namespace is not None
        assert f"{namespace.get('name')}-{namespace.get('version')}" == typelib_stem
        for element in root.iter():
            if element.tag.split("}")[-1] in ("include", "package"):
                reference = "-".join(
                    part for part in (element.get("name"), element.get("version")) if part
                )
                assert not FORBIDDEN.search(reference), (path, reference)

    for path in sorted(name for name in members if name.startswith("lib/pkgconfig/") and name.endswith(".pc")):
        contents = package.extractfile(path).read().decode(errors="replace")
        assert not FORBIDDEN.search(contents), f"GTK 3 dependency found in {path}"

print("PASS: packaged GIR/typelibs and build metadata contain no GTK 3/GDK 3 dependency")
