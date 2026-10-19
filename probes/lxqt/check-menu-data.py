#!/usr/bin/env python3
"""Compare packaged menus and translations with verified upstream inputs."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


SOURCE_SHA256 = "3487e47562dc19e63358a50c81e51cd0cf1a020397943cadd8db35daeb4866cc"


def require_equal(actual, expected, name):
    if actual != expected:
        raise RuntimeError("Package data differs: " + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--host-tools", type=Path, required=True)
    parser.add_argument("--perl", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    source_bytes = args.archive.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != SOURCE_SHA256:
        parser.error("The original lxqt-menu-data 2.4.0 archive differs")
    if args.work.exists():
        parser.error("The work directory must not exist")
    translator = (args.host_tools / "share/cmake/lxqt2-build-tools/modules/"
                  "LXQtTranslateDesktopYaml.pl")
    if not translator.is_file():
        parser.error("The matching LXQt host translation tool is absent")
    args.work.mkdir(parents=True)
    with tarfile.open(args.archive) as source:
        source.extractall(args.work, filter="data")
    root = args.work / "lxqt-menu-data-2.4.0/menu"
    with tarfile.open(args.package) as package:
        payload = {m.name: package.extractfile(m).read()
                   for m in package if m.isfile() and not m.name.startswith("+")}
    checked = []
    for path in sorted(root.glob("*.menu")):
        name = "share/examples/menus/" + path.name
        require_equal(payload[name], path.read_bytes(), name)
        checked.append(name)
    for path in sorted((root / "desktop-directories").glob("*.directory.in")):
        stem = path.name.removesuffix(".directory.in")
        # The upstream translator expands its third argument with Perl glob().
        translations = root / "translations" / (stem + "[_.]*directory.yaml")
        command = [str(args.perl), str(translator), str(path), stem, str(translations)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode or result.stderr:
            raise RuntimeError("The upstream translation tool failed: " + repr(result))
        name = "share/desktop-directories/" + stem + ".directory"
        require_equal(payload[name], result.stdout, name)
        if b"Name=" not in result.stdout or b"Name[" not in result.stdout:
            raise RuntimeError("The generated directory lacks translated names: " + name)
        checked.append(name)
    expected = set(payload) - {
        "share/cmake/lxqt-menu-data/lxqt-menu-data-config.cmake",
        "share/cmake/lxqt-menu-data/lxqt-menu-data-config-version.cmake",
    }
    if expected != set(checked) or not checked:
        raise RuntimeError("The package data inventory differs")
    if any(data.startswith(b"\x7fELF") for data in payload.values()):
        raise RuntimeError("The data package contains an ELF binary")
    for name in checked:
        try:
            require_equal(payload[name] + b"!", payload[name], name)
        except RuntimeError:
            continue
        raise RuntimeError("The comparator accepted a changed byte")
    result = {
        "scope": "packaged-menu-and-translation-data",
        "source_sha256": SOURCE_SHA256,
        "package_sha256": hashlib.sha256(args.package.read_bytes()).hexdigest(),
        "translator_sha256": hashlib.sha256(translator.read_bytes()).hexdigest(),
        "data_files": checked,
        "passed_data_files": len(checked),
        "changed_byte_refusals": len(checked),
        "runtime_session": "not-executed",
    }
    (args.work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
