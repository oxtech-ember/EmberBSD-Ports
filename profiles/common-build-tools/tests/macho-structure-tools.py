#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), structural Mach-O package metadata checks.
"""Exercise the real package resolver with byte fixtures and selected tools."""

import argparse
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import tempfile


def run(argv, **kwargs):
    result = subprocess.run(argv, text=True, capture_output=True, timeout=30, **kwargs)
    if result.returncode:
        raise AssertionError(f"{argv}: {result.stdout}{result.stderr}")
    return result.stdout


def thin(cpu, filetype=6, imports=()):
    commands = b""
    entries = ([(0xd, "@rpath/fixture.dylib")] if filetype == 6 else [])
    entries += [(0xc, name) for name in imports]
    for command, name in entries:
        encoded = name.encode() + b"\0"
        size = (24 + len(encoded) + 7) & ~7
        commands += struct.pack("<6I", command, size, 24, 0, 0, 0) + encoded.ljust(size - 24, b"\0")
    subtype = 3 if cpu == 0x01000007 else 0
    return struct.pack("<IiiIIIII", 0xfeedfacf, cpu, subtype, filetype, len(entries), len(commands), 0, 0) + commands


def executable(path, body):
    path.write_text('#!/bin/sh\nprintf called >> "$TRACE"\n' + body)
    path.chmod(0o755)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--patch", required=True)
    parser.add_argument("--bmake")
    parser.add_argument("--makeconf", type=Path)
    parser.add_argument("--make-arg", action="append", default=[])
    parser.add_argument("--od", required=True)
    parser.add_argument("--lipo", required=True)
    parser.add_argument("--otool", required=True)
    parser.add_argument("--awk", action="append", required=True)
    args = parser.parse_args()
    ports = Path(__file__).resolve().parents[3]
    patch = ports / "profiles/common-build-tools/patches/pkgsrc-macho-structure-tools.patch"
    files = re.findall(r"^--- a/(.+)$", patch.read_text(), re.M)
    with tempfile.TemporaryDirectory(prefix="macho-structure-") as temporary:
        work = Path(temporary)
        infrastructure = work / "infrastructure"
        for name in files:
            target = infrastructure / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.pkgsrc / name, target)
        output = run([args.patch, "-p1", "-F0", "-V", "none", "-i", str(patch)], cwd=infrastructure)
        assert not re.search(r"offset|fuzz|FAILED|reject", output, re.I), output
        print("PASS: structural patch applies without fuzz or offset")

        if args.makeconf:
            assert args.bmake
            # Keep all real pkgsrc includes. Only the five changed mk files differ.
            composed = work / "composed"
            composed.mkdir()
            for entry in args.pkgsrc.iterdir():
                destination = composed / entry.name
                if entry.name == "mk":
                    shutil.copytree(infrastructure / "mk", destination)
                    shutil.copytree(entry, destination, dirs_exist_ok=True,
                        ignore=lambda folder, names: [name for name in names
                            if (Path(folder) / name).relative_to(args.pkgsrc).as_posix() in files])
                elif entry.name in ("sysutils", "devel"):
                    destination.mkdir()
                    selected = {"file"} if entry.name == "sysutils" else {"py-vcs-versioning", "libtool-base"}
                    for package in entry.iterdir():
                        if package.name in selected:
                            shutil.copytree(package, destination / package.name)
                        else:
                            (destination / package.name).symlink_to(package)
                else:
                    destination.symlink_to(entry)
            variables = ("TOOL_DEPENDS", "TOOLS_DEPENDS.file", "USE_TOOLS", "MACHO_OD", "MACHO_LIPO", "MACHO_OTOOL")
            for package in ("devel/py-vcs-versioning", "devel/libtool-base", "sysutils/file"):
                argv = [args.bmake, "-r", "-C", str(composed / package),
                    "MAKECONF=" + str(args.makeconf.resolve()), "PKGSRCDIR=" + str(composed),
                    "WRKOBJDIR=" + str(work / "obj"), "MACHO_OD=" + shlex.quote(args.od),
                    "MACHO_LIPO=" + shlex.quote(args.lipo), "MACHO_OTOOL=" + shlex.quote(args.otool)]
                argv += args.make_arg
                for name in variables:
                    argv += ["-V", "${" + name + "}"]
                values = dict(zip(variables, run(argv).splitlines(), strict=True))
                assert not values["TOOLS_DEPENDS.file"], (package, values)
                assert "file" not in values["USE_TOOLS"].split(), (package, values)
                assert not re.search(r"(^| )file[<>=-]", values["TOOL_DEPENDS"]), (package, values)
                assert [values[name] for name in variables[-3:]] == [shlex.quote(args.od), shlex.quote(args.lipo), shlex.quote(args.otool)]
                if package == "sysutils/file":
                    assert "../../devel/libtool-base" in values["TOOL_DEPENDS"], values
            print("PASS: actual pkgsrc metadata: file -> libtool-base; no reverse file edge or implicit file tool")

        root = work / "stage"
        root.mkdir()
        fixtures = {
            "empty": b"", "text": b"a plain text file\n", "script": b"#!/bin/sh\nexit 0\n",
            "arm64.dylib": thin(0x0100000c), "x86_64.dylib": thin(0x01000007),
            "thin32.dylib": struct.pack("<IiiIIII", 0xfeedface, 7, 3, 1, 0, 0, 0),
            "java.class": bytes.fromhex("cafebabe0000003d0005") + b"\x01\0\x05Empty\x07\0\x01\x01\0\x10java/lang/Object\x07\0\x03" + struct.pack(">7H", 0x21, 2, 4, 0, 0, 0, 0),
            "short-macho": bytes.fromhex("cffaedfe"),
            "broken-commands": struct.pack("<IiiIIIII", 0xfeedfacf, 0x0100000c, 0, 6, 1, 16, 0, 0),
            "broken-fat": bytes.fromhex("cafebabe00000002"),
            "bad-fat-offset": struct.pack(">7I", 0xcafebabe, 1, 0x0100000c, 0, 0x200000, 32, 0),
        }
        for name, data in fixtures.items():
            (root / name).write_bytes(data)
        for name, option in (("fat.dylib", []), ("fat64.dylib", ["-fat64"])):
            run([args.lipo, "-create"] + option + [str(root / "arm64.dylib"), str(root / "x86_64.dylib"), "-output", str(root / name)])
        # The same import is valid only for an executable image.
        (root / "provider.dylib").write_bytes(thin(0x0100000c))
        for name, filetype in (("executable", 2), ("library", 6)):
            (root / name).write_bytes(thin(0x0100000c, filetype, ["@executable_path/provider.dylib"]))
        script = infrastructure / "mk/check/check-shlibs-macho.awk"
        (root / "Mach-O with spaces.dylib").write_bytes(fixtures["arm64.dylib"])
        poison = work / "poisoned-path"
        poison.mkdir()
        implicit_file = work / "implicit-file"
        (poison / "file").write_text('#!/bin/sh\necho implicit > ' + shlex.quote(str(implicit_file)) + '\nexit 99\n')
        (poison / "file").chmod(0o755)
        trace = work / "trace"
        env = dict(os.environ, MACHO_USE_LOAD_COMMANDS="yes", MACHO_OD=shlex.quote(args.od),
                   MACHO_LIPO=shlex.quote(args.lipo), MACHO_OTOOL=shlex.quote(args.otool),
                   DESTDIR="", CROSS_DESTDIR="", WRKDIR=str(work / "unrelated"),
                   PATH=str(poison) + ":" + os.environ.get("PATH", ""), TRACE=str(trace))

        def check(awk, name, expected="", overrides=None):
            output = run([awk, "-f", str(script)], input=str(root / name) + "\n", env=dict(env, **(overrides or {})))
            assert (expected in output) if expected else not output, (name, output)

        bad_od = work / "failed od"
        executable(bad_od, "echo cf fa ed fe 00 00 00 00\nexit 1\n")
        bad_lipo = work / "failed lipo"
        executable(bad_lipo, "echo arm64\nexit 1\n")
        bad_otool = work / "failed otool"
        executable(bad_otool, "printf 'magic cputype cpusubtype caps filetype ncmds sizeofcmds flags\\nMH_MAGIC_64 ARM64 ALL 0x00 EXECUTE 0 0 0\\n'\nexit 1\n")
        bad_load = work / "failed load commands"
        executable(bad_load, 'if [ "$3" = -hv ]; then exec ' + shlex.quote(args.otool) + ' "$@"; fi\necho "Load command 0"\nexit 1\n')
        for awk in args.awk:
            for name in ("empty", "text", "script", "java.class", "arm64.dylib", "x86_64.dylib", "thin32.dylib", "fat.dylib", "fat64.dylib", "executable", "Mach-O with spaces.dylib"):
                check(awk, name)
            for name in ("short-macho", "broken-commands", "broken-fat", "bad-fat-offset"):
                output = run([awk, "-f", str(script)], input=str(root / name) + "\n", env=env)
                assert "cannot read image" in output, (name, output)
            check(awk, "library", "unresolved library path: @executable_path/")
            check(awk, "arm64.dylib", "missing Mach-O tool selection", {"MACHO_OD": ""})
            for key, tool, expected in (("MACHO_OD", bad_od, "cannot read image signature"),
                    ("MACHO_LIPO", bad_lipo, "cannot read image architectures"),
                    ("MACHO_OTOOL", bad_otool, "cannot read image header"),
                    ("MACHO_OTOOL", bad_load, "unreadable load commands")):
                trace.unlink(missing_ok=True)
                check(awk, "arm64.dylib", expected, {key: shlex.quote(str(tool))})
                assert trace.read_text().startswith("called")
            assert not implicit_file.exists()
            print(f"PASS: {awk}: 11 valid/ignored fixtures, 4 malformed images, per-slice filetype and 5 tool-failure controls; no file command")


if __name__ == "__main__":
    main()
