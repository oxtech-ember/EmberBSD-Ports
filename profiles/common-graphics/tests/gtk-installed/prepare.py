#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), read-only installed GTK test-bundle preparation.
"""Package five unchanged GCC16 GTK test binaries and their actual test data."""
import argparse
import gzip
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sdk-source", "source", "archive", "package", "sysroot", "readelf", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15):
        parser.error("Python 3.15 is required.")
    sdk = Path(args.sdk_source).resolve(strict=True)
    sys.path.insert(0, str(sdk / "src"))
    import emberbsd_sdk
    from emberbsd_sdk import inventory, jsonio, paths, process
    if emberbsd_sdk.API_VERSION != 1:
        parser.error("SDK API 1 is required.")
    source, archive, package, sysroot, readelf = (Path(getattr(args, name)).resolve(strict=True)
        for name in ("source", "archive", "package", "sysroot", "readelf"))
    output = Path(paths.canonical_new(args.output))
    if output.exists():
        parser.error("The output directory must not exist.")
    for item in (source, sdk, sysroot, Path(__file__).resolve().parents[4]):
        paths.reject_overlap(str(output), str(item))
    if inventory.sha256_file(archive) != "80931fa472a77b9a164f6740e3c0b444fac6770054632d35a7ff9d679e5e7b9f":
        parser.error("The original GTK 3.24.52 source archive hash differs.")
    if inventory.sha256_file(package) != "8ffce9407f1965c3cfd7ade9d0e81ac5fc101fa7f1e84127c6075a734c722305":
        parser.error("The accepted GTK 3.24.52nb4 package hash differs.")
    output.mkdir()
    bundle = output / "gtk-upstream"
    bundle.mkdir()
    names = dict(builder=39, entry=2, textbuffer=11, treepath=6, window=7)
    compiled = source / "output"
    compile_commands = json.loads((compiled / "compile_commands.json").read_text())
    commands = {}
    case_paths = {}
    upstream = ["COPYING", "README.md", "testsuite/gtk/meson.build", "gtk/gtktestutils.c",
                *("testsuite/gtk/" + name + ".c" for name in names),
                *("gtk/" + path.name for path in sorted((source / "gtk").glob("*.gschema.xml")))]

    def copy(item, relative, mode=0o644):
        destination = bundle / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, destination)
        destination.chmod(mode)

    with tarfile.open(archive) as original:
        for relative in upstream:
            expected = original.extractfile("gtk-3.24.52/" + relative).read()
            assert (source / relative).read_bytes() == expected, relative
            copy(source / relative, "source/" + relative)
    for name in names:
        selected = [item for item in compile_commands if item["file"].endswith("/testsuite/gtk/" + name + ".c")]
        assert len(selected) == 1, name
        command = selected[0]["command"]
        assert command.startswith("aarch64--netbsd-gcc "), name
        assert "G_DISABLE_ASSERT" not in command and "G_DISABLE_CHECKS" not in command, name
        commands[name] = selected[0]
        copy(compiled / "testsuite/gtk" / name, "bin/" + name, 0o755)
        prefix = {"builder": "Builder", "textbuffer": "TextBuffer", "treepath": "tree-path"}.get(name, name)
        case_paths[name] = sorted(set(path.decode() for path in re.findall(
            rb"/" + prefix.encode() + rb"/[^\x00\n]{1,100}", (bundle / "bin" / name).read_bytes())))
        assert len(case_paths[name]) == names[name], name
    copy(compiled / "gtk/gschemas.compiled", "schemas/gschemas.compiled")
    for path in (source / "gtk").glob("*.gschema.xml"):
        copy(path, "schemas/" + path.name)
    copy(Path(__file__).with_name("run.sh"), "run.sh", 0o755)
    copy(Path(__file__).with_name("README.md"), "README.md")
    objects = {}

    def elf(item, label):
        regular = item.resolve(strict=True)
        if label.startswith("/"):
            assert regular.is_relative_to(sysroot), label
        data = regular.read_bytes()
        assert data[:6] == b"\x7fELF\x02\x01" and int.from_bytes(data[18:20], "little") == 183, label
        result = process.capture([str(readelf), "-W", "-h", "-l", "-d", str(regular)])
        description = result.stdout.decode()
        relative = "elf/" + re.sub(r"[^A-Za-z0-9_.-]", "_", label) + ".txt"
        (bundle / relative).parent.mkdir(exist_ok=True)
        (bundle / relative).write_bytes(result.stdout)
        rpaths = re.findall(r"\((?:RPATH|RUNPATH)\).*?\[([^]]+)\]", description)
        assert not any("/workspace" in path or "/tmp/" in path for path in rpaths), label
        needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", description)
        interpreter = re.findall(r"Requesting program interpreter: ([^]]+)\]", description)
        objects[label] = dict(sha256=inventory.sha256_file(regular), needed=needed, rpaths=rpaths,
                              interpreter=interpreter, evidence=relative)
        return needed

    queue = []
    for name in names:
        queue.extend(elf(bundle / "bin" / name, "test-" + name))
        assert objects["test-" + name]["interpreter"] == ["/usr/libexec/ld.elf_so"]
        assert objects["test-" + name]["rpaths"] == ["/usr/pkg/gcc16/lib:/usr/pkg/lib"]
    resolved = {}
    search = ("/usr/pkg/gcc16/lib", "/usr/pkg/lib", "/usr/lib", "/lib")
    while queue:
        soname = queue.pop(0)
        if soname in resolved:
            continue
        candidates = [Path(prefix) / soname for prefix in search if (sysroot / prefix[1:] / soname).is_file()]
        assert candidates, "Missing SDK dependency: " + soname
        target = candidates[0]
        resolved[soname] = str(target)
        queue.extend(elf(sysroot / str(target)[1:], str(target)))
    for relative in ("/usr/libexec/ld.elf_so", "/usr/bin/timeout"):
        elf(sysroot / relative[1:], relative)
    for name, directory in (("libgtk-3.so.0", "gtk"), ("libgdk-3.so.0", "gdk")):
        installed = sysroot / "usr/pkg/lib" / name
        built = compiled / directory / name
        assert inventory.sha256_file(installed.resolve(strict=True)) == inventory.sha256_file(built.resolve(strict=True)), name
    sdk_commit = process.capture(["git", "-C", str(sdk), "rev-parse", "HEAD"]).stdout.decode().strip()
    jsonio.write_json(bundle / "provenance.json", dict(status="PREPARED_NOT_EXECUTED", sdk_api=1,
        sdk_commit=sdk_commit, source_archive=dict(name=archive.name, sha256=inventory.sha256_file(archive),
            url="https://download.gnome.org/sources/gtk/3.24/gtk-3.24.52.tar.xz"),
        package=dict(name=package.name, sha256=inventory.sha256_file(package)),
        tests=names, case_paths=case_paths, expected_total=65, commands=commands, elf=objects, sdk_resolution=resolved,
        scope="Static AArch64 ELF/SDK closure and unchanged upstream-source verification. Target tests remain unrun."))
    files = sorted(path for path in bundle.rglob("*") if path.is_file())
    (bundle / "SHA256").write_text("".join(inventory.sha256_file(path) + "  " + path.relative_to(bundle).as_posix() + "\n" for path in files))
    target = output / "gtk-upstream.tgz"
    with target.open("xb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for path in sorted(bundle.rglob("*")):
                info = tar.gettarinfo(str(path), arcname="gtk-upstream/" + path.relative_to(bundle).as_posix())
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                info.mode = 0o755 if path.is_dir() or path.parent.name == "bin" or path.name == "run.sh" else 0o644
                if path.is_file():
                    with path.open("rb") as channel:
                        tar.addfile(info, channel)
                else:
                    tar.addfile(info)
    jsonio.write_json(output / "archive.json", dict(file=target.name, sha256=inventory.sha256_file(target), bytes=target.stat().st_size))
    print(f"PREPARED: {target}; 5 unchanged upstream binaries, 65 tests; target execution remains unrun.")


if __name__ == "__main__":
    main()
