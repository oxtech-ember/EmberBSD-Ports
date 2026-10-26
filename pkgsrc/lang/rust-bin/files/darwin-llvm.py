#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Isolate the upstream Rust LLVM on Darwin.
"""Change only the bundled LLVM identity and its actual Mach-O consumers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

OLD = "@rpath/libLLVM.dylib"
NEW = "@rpath/librustLLVM.dylib"
MAGIC = {bytes.fromhex(s) for s in ["feedface", "cefaedfe", "feedfacf", "cffaedfe", "cafebabe", "bebafeca", "cafebabf", "bfbafeca"]}
LOADS = {"LC_LOAD_DYLIB", "LC_LOAD_WEAK_DYLIB", "LC_REEXPORT_DYLIB", "LC_LOAD_UPWARD_DYLIB", "LC_LAZY_LOAD_DYLIB"}


def selected_tools(lipo, otool, install_name_tool, codesign):
    tools = dict(lipo=lipo, otool=otool, install_name_tool=install_name_tool, codesign=codesign)
    for name, value in tools.items():
        path = Path(value)
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f"Select an absolute executable for {name}")
    return {name: str(value) for name, value in tools.items()}


def signing_layout(path, arches, tools):
    """The pinned changed images have no policy metadata for LLVM to discard."""
    result = {}
    for arch in arches:
        process = subprocess.run([tools['codesign'], '--display', '--verbose=4',
                                  '--arch', arch, str(path)], capture_output=True, text=True, timeout=60)
        display = process.stderr
        directories = re.findall(r'^CodeDirectory .* flags=(0x[0-9a-fA-F]+)\([^\n]*\) hashes=([0-9]+)\+([0-9]+) ', display, re.M)
        if (process.returncode or len(directories) != 1 or int(directories[0][0], 16) != 0x20002
                or directories[0][2] != '0' or 'Signature=adhoc\n' not in display):
            raise ValueError(f"Unsupported Rust signing metadata; require plain ad-hoc linker-signed input: {path} ({arch})")
        result[arch] = {'flags': directories[0][0], 'special_slots': 0}
    return result


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(path, tools):
    result = {}
    arches = subprocess.check_output([tools["lipo"], "-archs", str(path)], text=True, timeout=60).split()
    if not arches:
        raise ValueError(f"No Mach-O architecture: {path}")
    for arch in arches:
        output = subprocess.check_output([tools["otool"], "-arch", arch, "-l", str(path)], text=True, timeout=60)
        image = dict(identity=None, imports=[], rpaths=[])
        command = None
        for line in output.splitlines():
            match = re.fullmatch(r"\s*cmd (LC_\w+)\s*", line)
            if match:
                command = match[1]
                continue
            match = re.fullmatch(r"\s*name (.+) \(offset \d+\)\s*", line)
            if match and command == "LC_ID_DYLIB":
                if image["identity"] is not None:
                    raise ValueError(f"Duplicate Mach-O identity: {path}")
                image["identity"] = match[1]
            elif match and command in LOADS:
                image["imports"].append([command, match[1]])
            match = re.fullmatch(r"\s*path (.+) \(offset \d+\)\s*", line)
            if match and command == "LC_RPATH":
                image["rpaths"].append(match[1])
        result[arch] = image
    return result


def inventory(prefix, tools):
    result = {}
    # Upstream component manifests put runtime images in these three trees.
    # Documentation and data remain unchanged and are not Mach-O scan inputs.
    paths = (path for name in ["bin", "lib", "libexec"] for path in (prefix / name).rglob("*"))
    for path in sorted(paths):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as stream:
            magic = stream.read(4)
        if magic in MAGIC:
            result[str(path.relative_to(prefix))] = inspect(path, tools)
    return result


def isolate(prefix, receipt, tools):
    tools = selected_tools(**tools)
    prefix = prefix.resolve(strict=True)
    provider = prefix / "lib/libLLVM.dylib"
    if sys.platform != "darwin" or provider.is_symlink() or not provider.is_file():
        raise ValueError("Use a fresh Darwin Rust staged prefix with a regular LLVM provider")
    if receipt.resolve().is_relative_to(prefix) or receipt.exists() or receipt.is_symlink():
        raise ValueError("Use a new build receipt outside the staged prefix")
    before = inventory(prefix, tools)
    for name, images in before.items():
        if any(image["identity"] == NEW or any(lib == NEW for _, lib in image["imports"]) for image in images.values()):
            raise ValueError(f"Use a fresh Rust stage without private LLVM identities or imports: {name}")
    providers = [name for name, images in before.items() if any(v["identity"] == OLD for v in images.values())]
    private = [name for name in providers if re.fullmatch(r"lib/rustlib/[^/]+/lib/libLLVM\.dylib", name)]
    if len(providers) != 2 or "lib/libLLVM.dylib" not in providers or len(private) != 1:
        raise ValueError("Unexpected upstream Rust LLVM provider layout")
    for name in providers:
        if any(v["identity"] != OLD for v in before[name].values()):
            raise ValueError(f"Mixed upstream LLVM identities: {name}")
    for name, images in before.items():
        for image in images.values():
            if any(lib.endswith("/libLLVM.dylib") and lib != OLD for _, lib in image["imports"]):
                raise ValueError(f"Unexpected upstream LLVM import: {name}")
    consumers = [name for name, images in before.items() if any(any(lib == OLD for _, lib in image["imports"]) for image in images.values())]
    if "bin/rustc" not in consumers or not any(re.fullmatch(r"lib/librustc_driver-[^/]+\.dylib", name) for name in consumers):
        raise ValueError("Missing upstream Rust LLVM consumers")
    if set(providers) & set(consumers):
        raise ValueError("Unexpected self-importing LLVM provider")
    translated = {name: str(Path(name).with_name("librustLLVM.dylib")) for name in providers}
    changed = providers + consumers
    storage = {}
    for name in changed:
        path = prefix / name
        info = path.stat()
        storage[name] = dict(device=info.st_dev, inode=info.st_ino, nlink=info.st_nlink)
        if info.st_nlink != 1 or not path.resolve().is_relative_to(prefix):
            raise ValueError(f"Use separate regular staged files: {name}")
    for name in translated.values():
        path = prefix / name
        if path.exists() or path.is_symlink():
            raise ValueError(f"Private LLVM name already exists: {name}")
    hashes = {name: digest(prefix / name) for name in changed}
    if len({hashes[name] for name in providers}) != 1:
        raise ValueError("The bundled LLVM providers have different bytes")
    signatures = {name: signing_layout(prefix / name, before[name], tools) for name in changed}
    for name, new in translated.items():
        (prefix / name).rename(prefix / new)
    commands = []

    def run(argv):
        process = subprocess.run(argv, text=True, capture_output=True, timeout=60)
        commands.append(dict(argv=argv, exit=process.returncode, stdout=process.stdout, stderr=process.stderr))
        if process.returncode:
            raise RuntimeError(f"{argv[0]} failed: {process.stderr}")

    for name in changed:
        path = prefix / translated.get(name, name)
        edits = ["-id", NEW] if name in providers else ["-change", OLD, NEW]
        run([tools["install_name_tool"]] + edits + [str(path)])
        # LLVM rewrites the plain linker signature; it needs no second signer.
        run([tools["codesign"], "--verify", "--strict", str(path)])
    after = inventory(prefix, tools)
    expected = json.loads(json.dumps(before))
    for name, new in translated.items():
        images = expected.pop(name)
        for image in images.values():
            image["identity"] = NEW
        expected[new] = images
    for name in consumers:
        for image in expected[name].values():
            image["imports"] = [[kind, NEW if lib == OLD else lib] for kind, lib in image["imports"]]
    if after != expected or any((prefix / name).exists() or (prefix / name).is_symlink() for name in providers):
        raise RuntimeError("The rewritten Mach-O graph differs from the selected LLVM changes")
    output = dict(before=before, after=after, providers=providers, consumers=consumers, changed=changed, storage=storage, signing_layout=signatures, before_sha256=hashes,
                  after_sha256={name: digest(prefix / translated.get(name, name)) for name in changed}, commands=commands)
    receipt.write_text(json.dumps(output, indent=2) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path)
    parser.add_argument('receipt', type=Path)
    for name in ('lipo', 'otool', 'install-name-tool', 'codesign'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        tools = selected_tools(args.lipo, args.otool, args.install_name_tool, args.codesign)
        result = isolate(args.prefix, args.receipt, tools)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from error
    print(f"Isolated Rust LLVM: {len(result['consumers'])} actual consumers")
