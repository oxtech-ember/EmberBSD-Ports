#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Prepare bounded target consumers for librsvg.
"""Build librsvg package consumers using only the selected target toolchain."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True

RENDERER_FILES = (
    "bin/rsvg-convert",
    "lib/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader_svg.so",
    "lib/girepository-1.0/Rsvg-2.0.typelib",
)
MIME_FILES = (
    "bin/update-mime-database",
    "share/mime/packages/freedesktop.org.xml",
)
UPSTREAM_FIXTURES = {
    "rsvg/tests/resources/Ahem.ttf":
        "b719ecb31c5b21fc573c03f6421c74ac63c271a5a3ff841e34f9705fb94b8448",
    "rsvg/tests/fixtures/reftests/rectangle.avif":
        "78333fa68dd739a122be7936b0f82a585a231cf9d863ba1ec6b91248a29afff0",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def existing(path):
    return Path(path).resolve(strict=True)


def new_work(path):
    require(os.path.isabs(path), "new absolute work path required")
    work = Path(os.path.abspath(path))
    require(not os.path.lexists(work), "new work path already exists")
    work.mkdir(parents=True)
    return work


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def run(command):
    result = subprocess.run(command, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError(result.stdout.decode("utf-8", "replace"))
    return result.stdout


def run_output(command, log_path):
    result = subprocess.run(command, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    Path(log_path).write_bytes(result.stdout)
    require(result.returncode == 0,
            result.stdout.decode("utf-8", "replace"))
    return result.stdout


def elf_needed(readelf, path):
    output = run([str(readelf), "-h", "-d", str(path)]).decode("utf-8", "replace")
    require(re.search(r"Machine:.*AArch64", output) is not None and
            re.search(r"Data:.*little endian", output) is not None,
            f"not an AArch64 little-endian ELF: {path}")
    return sorted(set(re.findall(r"\(NEEDED\).*\[([A-Za-z0-9._+-]+)\]", output)))


def selected_target_tools(tools, host_prefix_api):
    compiler = tools / "bin/aarch64--netbsd-clang"
    readelf = tools / "bin/aarch64--netbsd-readelf"
    binding = tools / "commands/commands.json"
    sdk_api = tools / "commands/sdk"
    require(compiler.is_file() and readelf.is_file() and binding.is_file() and sdk_api.is_dir(),
            "selected cross-tools binding is incomplete")
    record = json.loads(binding.read_text(encoding="utf-8"))
    require(record.get("format") == "emberbsd-compiler-binding" and
            record.get("version") == 1 and
            isinstance(record.get("commands", {}).get("cc"), list) and
            record["commands"]["cc"], "unsupported selected compiler binding")
    native_compiler = Path(record["commands"]["cc"][0]).resolve(strict=True)
    native_prefix = native_compiler.parent.parent
    require(compiler.resolve(strict=True) == (tools / "commands/cc").resolve(strict=True),
            "target Clang wrapper is not the selected SDK command binding")
    require(host_prefix_api.HOST_PREFIX_API == 2, "unsupported SDK host-prefix API")
    native_tools = host_prefix_api.load_host_prefix(native_prefix, required_roles=("readelf",))
    require(readelf.resolve(strict=True) ==
            Path(native_tools.tools["readelf"]).resolve(strict=True),
            "target readelf alias does not select the native-prefix reader")
    require(run([str(compiler), "-dumpmachine"]).decode("ascii").strip() ==
            "aarch64-unknown-netbsd", "selected compiler does not target EmberBSD AArch64")
    return compiler, readelf


def add_llvm_runtime_paths(command, sysroot, needed):
    runtime = sysroot / "usr/pkg/llvm/lib"
    providers = [name for name in needed if (runtime / name).is_file()]
    if providers:
        command.extend(["-L" + str(runtime), "-Wl,-rpath,/usr/pkg/llvm/lib",
                        "-Wl,-rpath-link," + str(runtime)])
    return providers


def css_only(sysroot, package_prefix, work, compiler, readelf):
    library = package_prefix / "lib/librsvg-2.so.2.63.4"
    header = package_prefix / "include/librsvg-2.0/librsvg/rsvg.h"
    require(library.is_file() and header.is_file(),
            "staged librsvg shared library/header is missing")
    needed = elf_needed(readelf, library)
    source = Path(__file__).with_name("librsvg-package.c").resolve(strict=True)
    includes = (
        "include/glib-2.0", "lib/glib-2.0/include", "include/cairo",
        "include/gdk-pixbuf-2.0", "include",
    )
    command = [str(compiler), "-O2", "-Wall", "-Wextra", "-Werror",
               "-DLIBRSVG_CSS_ONLY", "-I" + str(package_prefix / "include/librsvg-2.0")]
    command.extend("-I" + str(sysroot / "usr/pkg" / include) for include in includes)
    command.extend([str(source), "-L" + str(package_prefix / "lib"),
                    "-L" + str(sysroot / "usr/pkg/lib"),
                    "-Wl,-rpath,/usr/pkg/lib", "-Wl,-rpath-link," + str(sysroot / "usr/pkg/lib"),
                    "-lrsvg-2", "-lcairo", "-lgobject-2.0", "-lglib-2.0", "-Wl,--no-as-needed"])
    runtime = add_llvm_runtime_paths(command, sysroot, needed)
    command.extend("-l:" + name for name in needed)
    command.extend(["-o", str(work / "librsvg-css-package")])
    (work / "compile.command").write_text(shlex.join(command) + "\n", encoding="utf-8")
    run_output(command, work / "compile.log")
    linked = run([str(readelf), "-d", str(work / "librsvg-css-package")]).decode("utf-8", "replace")
    linked_needed = set(re.findall(r"\(NEEDED\).*\[([^\]]+)\]", linked))
    require(set(needed).issubset(linked_needed),
            "CSS consumer omits a direct staged librsvg provider")
    (work / "runtime-library-dirs.txt").write_text(
        "/usr/pkg/llvm/lib\n" if runtime else "", encoding="utf-8")
    inputs = [source, library, header, work / "librsvg-css-package",
              work / "runtime-library-dirs.txt"]
    (work / "inputs.sha256").write_text(
        "".join(f"{digest(path)}  {path}\n" for path in inputs), encoding="utf-8")
    print("PASS: built focused AArch64 librsvg CSS C consumer; direct runtime providers recorded")


def package_entries(archive, expected_name):
    with tarfile.open(archive, "r:gz") as package:
        contents = package.extractfile("+CONTENTS")
        require(contents is not None and
                any(line.strip() == "@name " + expected_name
                    for line in contents.read().decode("utf-8", "replace").splitlines()),
                f"wrong package archive: {expected_name}")
        entries = []
        for member in package.getmembers():
            relative = member.name.removeprefix("./")
            if relative.startswith("+") or member.isdir():
                continue
            require(not relative.startswith("/") and ".." not in Path(relative).parts,
                    f"unsafe package entry: {relative}")
            if member.issym():
                entries.append((relative, "symlink", member.linkname, None))
            elif member.isfile():
                stream = package.extractfile(member)
                require(stream is not None, f"cannot read package entry: {relative}")
                data = stream.read()
                entries.append((relative, "file", None, data))
            else:
                raise RuntimeError(f"unexpected package entry type: {relative}")
        return entries


def verify_archive(archive, expected_name, installed_roots, expected_files):
    manifest = []
    names = set()
    for relative, kind, link, data in package_entries(archive, expected_name):
        names.add(relative)
        for root in installed_roots:
            installed = root / relative
            if kind == "symlink":
                require(installed.is_symlink() and os.readlink(installed) == link,
                        f"installed symlink differs: {installed}")
                manifest.append(f"symlink {link}  {installed}\n")
            else:
                require(not installed.is_symlink() and installed.is_file() and
                        installed.read_bytes() == data,
                        f"installed payload differs: {installed}")
                manifest.append(f"{hashlib.sha256(data).hexdigest()}  {installed}\n")
    require(set(expected_files).issubset(names), f"incomplete package: {expected_name}")
    return names, manifest


def full_consumer(sysroot, package, mime_package, source, package_prefix, work,
                  tools, compiler, readelf):
    package_names, manifest = verify_archive(
        package, "librsvg-2.63.4nb1", [package_prefix, sysroot / "usr/pkg"],
        RENDERER_FILES)
    mime_names, mime_manifest = verify_archive(
        mime_package, "shared-mime-info-2.5.1", [sysroot / "usr/pkg"], MIME_FILES)
    manifest.extend(mime_manifest)
    require("lib/librsvg-2.so.2.63.4" in package_names,
            "incomplete renderer shared library")
    fixture_paths = {}
    for relative, expected in UPSTREAM_FIXTURES.items():
        path = source / relative
        require(digest(path) == expected, f"upstream fixture differs: {path}")
        fixture_paths[relative] = path
    files = [
        ("rsvg-convert", package_prefix / RENDERER_FILES[0], "0700"),
        ("svg-loader.so", package_prefix / RENDERER_FILES[1], "0600"),
        ("query-loaders", sysroot / "usr/pkg/bin/gdk-pixbuf-query-loaders", "0700"),
        ("Ahem.ttf", fixture_paths["rsvg/tests/resources/Ahem.ttf"], "0600"),
        ("font-README.md", source / "rsvg/tests/resources/README.md", "0600"),
        ("librsvg-AUTHORS", source / "AUTHORS", "0600"),
        ("librsvg-COPYING.LIB", source / "COPYING.LIB", "0600"),
        ("update-mime-database", sysroot / "usr/pkg/bin/update-mime-database", "0700"),
        ("mime/packages/freedesktop.org.xml",
         sysroot / "usr/pkg/share/mime/packages/freedesktop.org.xml", "0600"),
    ]
    namespaces = ("GLib-2.0", "GObject-2.0", "Gio-2.0", "cairo-1.0",
                  "GdkPixbuf-2.0", "Rsvg-2.0")
    typelibs = []
    for name in namespaces:
        root = package_prefix if name == "Rsvg-2.0" else sysroot / "usr/pkg"
        typelibs.append((name, root / "lib/girepository-1.0" / (name + ".typelib"), "0600"))
    header = ('struct fixture { const char *name; const unsigned char *start, *end; mode_t mode; };\n')
    assembly = ".section .rodata\n"
    for group_index, group in enumerate((files, typelibs)):
        for index, (_name, path, _mode) in enumerate(group):
            symbol = f"blob_{group_index}_{index}"
            header += f"extern const unsigned char {symbol}_start[], {symbol}_end[];\n"
            assembly += (f'.balign 8\n.global {symbol}_start, {symbol}_end\n{symbol}_start:\n'
                         f'.incbin "{path}"\n{symbol}_end:\n')
            manifest.append(f"{digest(path)}  {path}\n")
        kind = "files" if group_index == 0 else "typelibs"
        header += f"static const struct fixture {kind}[] = {{\n"
        for index, (name, _path, mode) in enumerate(group):
            header += f'{{"{name}", blob_{group_index}_{index}_start, blob_{group_index}_{index}_end, {mode}}},\n'
        header += "};\n"
    avif = fixture_paths["rsvg/tests/fixtures/reftests/rectangle.avif"]
    avif_svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='20' height='10'>"
                "<image href='data:image/avif;base64," +
                base64.b64encode(avif.read_bytes()).decode("ascii") + "'/></svg>")
    header += f"static const char avif_svg[] = {c_string(avif_svg)};\n"
    header += ('static const char text_svg[] = "<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'32\' height=\'16\'><text x=\'1\' y=\'12\' font-family=\'Ahem\' font-size=\'10\'>XX</text></svg>";\n')
    assembly += '.section .note.GNU-stack,"",@progbits\n'
    (work / "librsvg-fixtures.h").write_text(header, encoding="utf-8")
    (work / "librsvg-fixtures.S").write_text(assembly, encoding="utf-8")
    elf_files = [item for item in files if item[2] == "0700" or item[0] == "svg-loader.so"]
    elf_files.append(("librsvg library", package_prefix / "lib/librsvg-2.so.2.63.4", "0600"))
    needed = sorted({name for _label, path, _mode in elf_files for name in elf_needed(readelf, path)})
    source_c = Path(__file__).with_name("librsvg-package.c").resolve(strict=True)
    include_dirs = ("include/glib-2.0", "lib/glib-2.0/include", "include/gdk-pixbuf-2.0",
                    "include/cairo", "include")
    command = [str(compiler), "-O2", "-Wall", "-Wextra", "-Werror",
               "-I" + str(work), "-I" + str(package_prefix / "include/librsvg-2.0")]
    command.extend("-I" + str(sysroot / "usr/pkg" / item) for item in include_dirs)
    command.extend([str(source_c), str(work / "librsvg-fixtures.S"),
                    "-L" + str(package_prefix / "lib"), "-L" + str(sysroot / "usr/pkg/lib"),
                    "-Wl,-rpath,/usr/pkg/lib", "-Wl,-rpath-link," + str(sysroot / "usr/pkg/lib"),
                    "-lrsvg-2", "-lgdk_pixbuf-2.0", "-lcairo", "-lfontconfig",
                    "-lgirepository-2.0", "-lgobject-2.0", "-lglib-2.0", "-Wl,--no-as-needed"])
    runtime = add_llvm_runtime_paths(command, sysroot, needed)
    command.extend("-l:" + name for name in needed)
    command.extend(["-o", str(work / "librsvg-package")])
    (work / "compile.command").write_text(shlex.join(command) + "\n", encoding="utf-8")
    run_output(command, work / "compile.log")
    linked = run([str(readelf), "-d", str(work / "librsvg-package")]).decode("utf-8", "replace")
    linked_needed = set(re.findall(r"\(NEEDED\).*\[([^\]]+)\]", linked))
    require(set(needed).issubset(linked_needed),
            "full consumer omits a dynamic provider required by an embedded program/module")
    (work / "runtime-library-dirs.txt").write_text(
        "/usr/pkg/llvm/lib\n" if runtime else "", encoding="utf-8")
    manifest.extend(f"{digest(path)}  {path}\n" for path in
                    (Path(__file__), source_c, package, mime_package, avif,
                     work / "librsvg-package", work / "runtime-library-dirs.txt"))
    (work / "inputs.sha256").write_text("".join(manifest), encoding="utf-8")
    print("PASS: renderer/MIME archive payloads, upstream fixtures, and target consumer providers verified")


def c_string(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--css-only", action="store_true",
                        help="build only the focused installed librsvg CSS C consumer")
    parser.add_argument("--sdk-source", default=os.environ.get("EMBERBSD_SDK_SOURCE"),
                        help="selected EmberBSD SDK source; defaults to EMBERBSD_SDK_SOURCE")
    parser.add_argument("paths", nargs="+")
    options = parser.parse_args()
    require(sys.version_info[:2] == (3, 15), "use the selected build-host Python 3.15")
    require(options.sdk_source and os.path.isabs(options.sdk_source),
            "set --sdk-source or EMBERBSD_SDK_SOURCE to an absolute selected SDK source")
    sdk_root = Path(options.sdk_source).resolve(strict=True)
    sdk_package = sdk_root / "src/emberbsd_sdk"
    require((sdk_package / "__init__.py").is_file(), "selected SDK source lacks emberbsd_sdk")
    sys.path.insert(0, str(sdk_root / "src"))
    import emberbsd_sdk
    require(type(emberbsd_sdk.API_VERSION) is int and emberbsd_sdk.API_VERSION == 1 and
            Path(emberbsd_sdk.__file__).resolve().parent == sdk_package.resolve(),
            "selected SDK source does not provide API version 1")
    from emberbsd_sdk import host_prefix
    expected = 4 if options.css_only else 7
    require(len(options.paths) == expected,
            "CSS mode: TOOLS SYSROOT PACKAGE_STAGE_PREFIX NEW_WORK; full mode: TOOLS SYSROOT LIBRSVG_PACKAGE MIME_PACKAGE SOURCE PACKAGE_STAGE_PREFIX NEW_WORK")
    resolved = list(map(existing, options.paths[:-1]))
    work = new_work(options.paths[-1])
    if options.css_only:
        tools, sysroot, package_prefix = resolved
        compiler, readelf = selected_target_tools(tools, host_prefix)
        css_only(sysroot, package_prefix, work, compiler, readelf)
    else:
        tools, sysroot, package, mime_package, source, package_prefix = resolved
        require(all(re.fullmatch(r"/[A-Za-z0-9_./-]+", str(path))
                    for path in (sysroot, source, package_prefix)),
                "unsafe path for assembler .incbin input")
        compiler, readelf = selected_target_tools(tools, host_prefix)
        full_consumer(sysroot, package, mime_package, source, package_prefix, work,
                      tools, compiler, readelf)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
