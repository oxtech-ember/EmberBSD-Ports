#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc font runtime-role regression.
"""Check shared native/cross font dependencies without compiling or installing."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sdk-source", "pkgsrc", "native-makeconf", "cross-makeconf", "bmake", "work"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15):
        parser.error("Python 3.15 is required.")
    sdk = Path(args.sdk_source).resolve(strict=True)
    sys.path.insert(0, str(sdk / "src"))
    import emberbsd_sdk
    from emberbsd_sdk import inventory, jsonio, paths, process
    from emberbsd_sdk.errors import CommandError
    if emberbsd_sdk.API_VERSION != 1:
        parser.error("SDK library API 1 is required.")
    root = Path(__file__).resolve().parents[3]
    pkgsrc = Path(args.pkgsrc).resolve(strict=True)
    bmake = Path(args.bmake).resolve(strict=True)
    configs = {role: Path(getattr(args, role + "_makeconf")).resolve(strict=True)
               for role in ("native", "cross")}
    work = Path(paths.canonical_new(args.work))
    if work.exists():
        parser.error("The work directory must not exist.")
    for source in (pkgsrc, root, sdk):
        paths.reject_overlap(str(work), str(source))
    work.mkdir()
    commands = []

    def run(label, argv, *, cwd=work, data=None):
        argv = [str(item) for item in argv]
        try:
            result = process.capture(argv, cwd=str(cwd), env=dict(os.environ, LC_ALL="C"), input=data)
            stdout, stderr, status = result.stdout, result.stderr, result.returncode
        except CommandError as error:
            stdout, stderr, status = error.stdout, error.stderr, error.returncode
        (work / (label + ".stdout")).write_bytes(stdout)
        (work / (label + ".stderr")).write_bytes(stderr)
        commands.append(dict(label=label, argv=argv, status=status))
        jsonio.write_json(work / "commands.json", commands, exclusive=False)
        if status:
            raise SystemExit(f"Unexpected result for {label}: {status}; inspect {work}.")
        return stdout.decode("utf-8")

    recipes = ("font-misc-misc", "font-cursor-misc", "dejavu-ttf", "font-adobe-utopia-type1")
    originals = {
        "mk/pkginstall/bsd.pkginstall.mk": "66e8b3233756d88d80cac6cb2fb904105c818cacdac18674b8e4c99faf0e7fd2",
        "mk/pkgtasks/fonts.mk": "7a29bb11a3a6e11217a1acecd876b20f0845e6a5b3f0eb9e35575b05b2457a69",
    }
    patch = root / "profiles/common-build-tools/patches/pkgsrc-font-runtime-roles.patch"
    delta = patch.read_bytes()
    trees = {}
    for variant in ("before", "after"):
        tree = work / variant
        tree.mkdir()
        for item in pkgsrc.iterdir():
            if item.name not in ("mk", "fonts"):
                (tree / item.name).symlink_to(item, target_is_directory=item.is_dir())
        shutil.copytree(pkgsrc / "mk", tree / "mk")
        (tree / "fonts").mkdir()
        for item in (pkgsrc / "fonts").iterdir():
            destination = tree / "fonts" / item.name
            if item.name in recipes:
                shutil.copytree(item, destination)
            else:
                destination.symlink_to(item, target_is_directory=item.is_dir())
        if any(inventory.sha256_file(tree / name) != digest for name, digest in originals.items()):
            run(variant + "-reverse", ["patch", "-R", "-f", "-F", "0", "-p1", "-d", tree], data=delta)
        assert all(inventory.sha256_file(tree / name) == digest for name, digest in originals.items())
        if variant == "after":
            run("apply-shared-delta", ["patch", "-f", "-F", "0", "-p1", "-d", tree], data=delta)
        trees[variant] = tree

    variables = ("PKG_FAIL_REASON", "DEPENDS", "TOOL_DEPENDS", "USE_TOOLS", "FILES_SUBST",
                 "X11BASE", "TOOLBASE", "TOOLS_PATH.bdftopcf", "TOOLS_PATH.ucs2any",
                 "TOOLS_PATH.gzip", "_TOOLS_DEPMETHOD.bdftopcf", "_TOOLS_DEPMETHOD.ucs2any",
                 "CC_VERSION", "USE_CROSS_COMPILE", "NATIVE_CC", "CC")
    metadata = {}
    for variant, tree in trees.items():
        for role, original_config in configs.items():
            for framework in ("no", "yes"):
                for recipe in recipes:
                    label = "-".join((variant, role, framework, recipe))
                    config = work / (label + ".conf")
                    config.write_text(f'.include "{original_config}"\n.if defined(BSD_PKG_MK)\n'
                        f'WRKOBJDIR={work / "objects" / label}\n.endif\n')
                    argv = [bmake, "MAKECONF=" + str(config), "_USE_NEW_PKGINSTALL=" + framework]
                    for variable in variables:
                        argv += ["-V", "${" + variable + "}"]
                    lines = run(label, argv, cwd=tree / "fonts" / recipe).splitlines()
                    assert len(lines) == len(variables), (label, lines)
                    selected = dict(zip(variables, lines))
                    metadata[label] = selected
                    assert selected["CC_VERSION"].startswith("gcc-16"), (label, selected["CC_VERSION"])
                    assert (selected["USE_CROSS_COMPILE"].lower() == "yes") == (role == "cross")
                    substitutions = dict(word.split("=", 1) for word in shlex.split(selected["FILES_SUBST"]) if "=" in word)
                    if role == "cross":
                        rejected = "not supported in cross-compilation" in selected["PKG_FAIL_REASON"]
                        assert rejected == (variant == "before"), (label, selected["PKG_FAIL_REASON"])
                        if variant == "after":
                            assert "mkfontscale>=1.2:../../fonts/mkfontscale" in selected["DEPENDS"].split()
                            assert "encodings-[0-9]*:../../fonts/encodings" in selected["DEPENDS"].split()
                            assert not any(word.startswith(("mkfontdir:", "mkfontscale:")) for word in selected["USE_TOOLS"].split())
                            assert not any(word.startswith("mkfontscale") for word in selected["TOOL_DEPENDS"].split())
                            assert substitutions["MKFONTDIR"] == selected["X11BASE"] + "/bin/mkfontdir"
                            if framework == "yes":
                                assert substitutions["MKFONTSCALE"] == selected["X11BASE"] + "/bin/mkfontscale"
                            elif recipe == "dejavu-ttf":
                                assert substitutions["TTF_INDEX_CMD"] == selected["X11BASE"] + "/bin/mkfontscale"
                            elif recipe == "font-adobe-utopia-type1":
                                assert substitutions["TYPE1_INDEX_CMD"] == selected["X11BASE"] + "/bin/mkfontscale"
                            assert selected["X11BASE"] != selected["TOOLBASE"]
                    if variant == "after":
                        previous = metadata[label.replace("after-", "before-", 1)]
                        if role == "native":
                            for name in ("DEPENDS", "TOOL_DEPENDS", "USE_TOOLS"):
                                assert selected[name] == previous[name], (label, name)
                            old_substitutions = dict(word.split("=", 1) for word in shlex.split(previous["FILES_SUBST"]) if "=" in word)
                            for name in ("MKFONTDIR", "MKFONTSCALE", "TTF_INDEX_CMD", "TYPE1_INDEX_CMD"):
                                assert substitutions.get(name) == old_substitutions.get(name), (label, name)
                        for name in variables[7:]:
                            assert selected[name] == previous[name], (label, name)
                        if recipe in ("font-misc-misc", "font-cursor-misc"):
                            assert selected["_TOOLS_DEPMETHOD.bdftopcf"] == "TOOL_DEPENDS"
                            assert selected["TOOLS_PATH.bdftopcf"].startswith(selected["TOOLBASE"] + "/")
                        if recipe == "font-misc-misc":
                            assert selected["_TOOLS_DEPMETHOD.ucs2any"] == "TOOL_DEPENDS"

    # The repair must not relax the tools framework's explicit cross refusal.
    for framework in ("no", "yes"):
        label = "explicit-run-tool-" + framework
        config = work / (label + ".conf")
        config.write_text(f'.include "{configs["cross"]}"\n.if defined(BSD_PKG_MK)\n'
            f'WRKOBJDIR={work / "objects" / label}\nUSE_TOOLS+=mkfontdir:run\n.endif\n')
        reason = run(label, [bmake, "MAKECONF=" + str(config), "_USE_NEW_PKGINSTALL=" + framework,
            "-V", "${PKG_FAIL_REASON}"],
            cwd=trees["after"] / "fonts/font-misc-misc")
        assert "mkfontdir:run not supported in cross-compilation" in reason
    for name in ("mk/tools/replace.mk", "mk/pkginstall/fonts"):
        assert (trees["before"] / name).read_bytes() == (trees["after"] / name).read_bytes()
    export = (root / "pkgsrc/export.conf").read_text()
    assert "font-cross.patch" not in export
    assert not (root / "probes/plasma-mobile/toolkit/font-cross.patch").exists()
    assert export.count("pkgsrc-font-runtime-roles.patch") == 1
    assert "patch\tprofiles/common-build-tools/patches/pkgsrc-font-runtime-roles.patch\n" in export
    sdk_commit = run("sdk-commit", ["git", "-C", sdk, "rev-parse", "HEAD"]).strip()
    jsonio.write_json(work / "result.json", dict(status="PASS", sdk_api=1, sdk_commit=sdk_commit,
        scope="32 actual recipe/framework/native/cross metadata cases and two strict refusal controls. No package or target execution.",
        metadata=metadata, inputs={str(path): inventory.sha256_file(path) for path in
        (patch, Path(__file__).resolve(), *configs.values())}))
    print("PASS: 32 actual font metadata cases; native generators, target indexers and two strict refusal controls.")


if __name__ == "__main__":
    main()
