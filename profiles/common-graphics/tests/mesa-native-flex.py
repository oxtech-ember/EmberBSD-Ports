#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check real pkgsrc routing and Mesa lexers.
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile


def digest(path, algorithm):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def main():
    if len(sys.argv) != 5:
        raise SystemExit("Usage: mesa-native-flex.py PKGSRC MAKECONF MESA_ARCHIVE NEW_WORK")
    source, config, archive = (Path(arg).resolve(strict=True) for arg in sys.argv[1:4])
    work = Path(sys.argv[4])
    if not work.is_absolute() or work.exists() or work.is_symlink():
        raise SystemExit("Use a new absolute work directory")
    work.mkdir(parents=True)
    profile = Path(__file__).resolve().parent.parent
    recipe = profile / "../../pkgsrc/graphics/MesaLib"
    bmake = shutil.which(os.environ.get("BMAKE", "bmake"))
    if bmake is None:
        raise SystemExit("Actual bmake is required")
    commands = []

    def run(label, argv):
        result = subprocess.run([str(arg) for arg in argv], text=True, capture_output=True, check=False)
        (work / (label + ".stdout")).write_text(result.stdout)
        (work / (label + ".stderr")).write_text(result.stderr)
        commands.append({"label": label, "argv": [str(arg) for arg in argv], "status": result.returncode})
        (work / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if result.returncode:
            raise AssertionError(f"{label} failed: {result.stderr}")
        return result.stdout

    first = '''.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Mesa lexers handle yywrap themselves. Flex only generates source on the host.
TOOL_DEPENDS+=\tflex>=2.5.4a:../../devel/flex
TOOLS_PLATFORM.flex=\t${TOOLBASE}/bin/flex
.endif
'''
    last = '''
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${_TOOLS_USE_PKGSRC.flex:Uyes:tl} != "no"
PKG_FAIL_REASON+= "Mesa cross builds require installed native Flex satisfying FLEX_REQD=${FLEX_REQD} at ${TOOLBASE}/bin/flex"
.endif
'''
    views = {}
    for variant in ("before", "after"):
        tree = work / variant / "pkgsrc"
        (tree / "graphics").mkdir(parents=True)
        for entry in source.iterdir():
            if not entry.name.startswith(".") and entry.name != "graphics":
                (tree / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
        for entry in (source / "graphics").iterdir():
            if entry.name != "MesaLib":
                (tree / "graphics" / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
        views[variant] = tree / "graphics/MesaLib"
        shutil.copytree(recipe, views[variant])
    makefile = views["before"] / "Makefile"
    body = makefile.read_text()
    if body.count(first) != 1 or not body.endswith(last):
        raise AssertionError("Unexpected Mesa source repair")
    makefile.write_text(body.replace(first, "", 1).removesuffix(last))
    fields = ("PKGNAME PKG_FAIL_REASON BUILD_DEPENDS DEPENDS TOOL_DEPENDS TOOLS_PATH.flex "
              "_TOOLS_USE_PKGSRC.flex _TOOLS_VERSION.flex FLEX_REQD TOOLBASE WRKDIR MESON_ARGS").split()

    def query(label, variant, extra=()):
        argv = [bmake, "-C", views[variant], "MAKECONF=" + str(config),
                "WRKOBJDIR=" + str(work / variant / "objects"), *extra]
        for field in fields:
            argv.extend(("-V", "${" + field + "}"))
        values = run(label, argv).splitlines()
        if len(values) != len(fields):
            raise AssertionError("Unexpected bmake metadata output")
        return dict(zip(fields, values))

    before, after = query("before-cross", "before"), query("after-cross", "after")
    if not any(entry.startswith("flex>=") for entry in before["BUILD_DEPENDS"].split()):
        raise AssertionError("Real baseline target Flex dependency was not reproduced")
    if any(entry.startswith("flex>=") for field in ("BUILD_DEPENDS", "DEPENDS") for entry in after[field].split()):
        raise AssertionError("Target Flex dependency remains")
    flex = Path(after["TOOLBASE"]) / "bin/flex"
    if (after["PKG_FAIL_REASON"] or after["_TOOLS_USE_PKGSRC.flex"] != "no"
            or after["TOOLS_PATH.flex"] != str(flex)
            or "flex>=2.5.4a:../../devel/flex" not in after["TOOL_DEPENDS"].split()):
        raise AssertionError("Installed native Flex routing failed")
    for field in ("PKGNAME", "DEPENDS", "MESON_ARGS"):
        if before[field] != after[field]:
            raise AssertionError("Unrelated cross metadata changed: " + field)
    native = [query("before-native", "before", ("USE_CROSS_COMPILE=no",)),
              query("after-native", "after", ("USE_CROSS_COMPILE=no",))]
    for field in fields:
        if field != "WRKDIR" and native[0][field] != native[1][field]:
            raise AssertionError("Native metadata changed: " + field)
    for label, flags in (
        ("missing", ("TOOLS_PLATFORM.flex=" + str(work / "absent-flex"),)),
        ("wrong", ("TOOLS_PLATFORM.flex=/usr/bin/false",)),
        ("too-old", ("FLEX_REQD=999",)),
    ):
        bad = query(label, "after", flags)
        if "Mesa cross builds require installed native Flex" not in bad["PKG_FAIL_REASON"]:
            raise AssertionError("Invalid native Flex was accepted: " + label)

    expected = re.search(r"^SHA512 \(" + re.escape(archive.name) + r"\) = ([0-9a-f]{128})$",
                         (recipe / "distinfo").read_text(), re.MULTILINE)
    archive_hash = digest(archive, "sha512")
    if expected is None or archive_hash != expected[1]:
        raise AssertionError("Pinned Mesa source archive differs")
    lexers = []
    source_dir = work / "source"
    with tarfile.open(archive, "r|xz") as bundle:
        for member in bundle:
            if not member.isfile() or not member.name.endswith((".l", ".ll")):
                continue
            relative = Path(member.name)
            if relative.parts[0] != "mesa-26.2.5" or ".." in relative.parts:
                raise AssertionError("Unexpected source member")
            path = source_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bundle.extractfile(member).read())
            text = path.read_text()
            if not (re.search(r"^%option[^\n]*\bnoyywrap\b", text, re.MULTILINE)
                    or re.search(r"int\s+yywrap\s*\(\s*\)\s*\{\s*return\s+-?1\s*;\s*\}", text)):
                raise AssertionError("Mesa lexer no longer owns yywrap: " + member.name)
            lexers.append(path)
    if len(lexers) != 6:
        raise AssertionError("Unexpected Mesa lexer set")
    generated = work / "generated"
    generated.mkdir()
    outputs = []
    run("flex-version", [flex, "--version"])
    for index, lexer in enumerate(sorted(lexers)):
        output = generated / (str(index) + (".cpp" if lexer.suffix == ".ll" else ".c"))
        run("lexer-" + str(index), [flex, "-o", output, lexer])
        if "YY_FLEX_MAJOR_VERSION" not in output.read_text():
            raise AssertionError("Real Flex scanner was not generated")
        outputs.append({"source": str(lexer), "source_sha256": digest(lexer, "sha256"),
                        "output": str(output), "output_sha256": digest(output, "sha256")})
    receipt = {"status": "PASS", "scope": "Actual baseline/fixed/native pkgsrc metadata, three invalid-provider refusals, pinned upstream yywrap ownership and six genuine native Flex generations; no target compilation, package or VM acceptance.",
               "before": before, "after": after, "native": native, "archive_sha512": archive_hash,
               "flex_sha256": digest(flex, "sha256"), "lexers": outputs}
    (work / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("PASS: native Flex routing, unchanged native policy, invalid-provider refusals and six upstream Mesa lexers")


if __name__ == "__main__":
    main()
