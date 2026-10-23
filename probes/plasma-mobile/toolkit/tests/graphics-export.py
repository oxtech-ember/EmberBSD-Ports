#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check graphics patch composition and native/cross metadata without a build."""
import sys
sys.dont_write_bytecode = True
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil

KEYS = """PKGNAME PKG_FAIL_REASON MESON_ARGS PLIST.introspection TOOLBASE
TOOL_DEPENDS MESON_BINARY.glib-mkenums MESON_BINARY.glib-genmarshal
MAKE_ENV MESON_CROSS.emberbsd_gi_cross PKG_OPTIONS PLIST.doc PLIST.vala""".split()
RECIPES = ("sysutils/libnotify", "sysutils/gsettings-desktop-schemas", "www/libproxy")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_metadata(recipe, mode, values, plist):
    cross = mode == "yes"
    options = shlex.split(values["MESON_ARGS"])
    introspection = [v for v in options if v.startswith("-Dintrospection=")]
    bindings = values["PLIST.introspection"] == "yes"
    errors = shlex.split(values["PKG_FAIL_REASON"])
    environment = dict(v.split("=", 1) for v in shlex.split(values["MAKE_ENV"]))
    if recipe.endswith("libnotify"):
        require(values["PKGNAME"] == "libnotify-0.8.9", "Wrong libnotify release")
        expected = "disabled" if cross else "enabled"
        require(introspection == ["-Dintrospection=" + expected], "libnotify GI selection changed")
        require(bindings != cross, "libnotify PLIST selection changed")
        require(not errors, "libnotify prerequisites failed: " + repr(errors))
        if cross:
            for name in ("glib-mkenums", "glib-genmarshal"):
                require(values["MESON_BINARY." + name] == values["TOOLBASE"] + "/bin/" + name,
                        "libnotify did not select the native " + name)
        else:
            require("glib2-introspection-" in values["TOOL_DEPENDS"], "Native GI tool was removed")
    elif recipe.endswith("gsettings-desktop-schemas"):
        require(values["PKGNAME"] == "gsettings-desktop-schemas-51.0", "Wrong schema release")
        require(introspection == ["-Dintrospection=true"] and bindings,
                "The complete toolkit lost GDesktopEnums bindings")
        for name in ("lib/girepository-1.0/GDesktopEnums-3.0.typelib",
                     "share/gir-1.0/GDesktopEnums-3.0.gir"):
            require("${PLIST.introspection}" + name in plist.splitlines(), "Missing binding: " + name)
        if cross:
            require(values["MESON_BINARY.glib-mkenums"] == values["TOOLBASE"] + "/bin/glib-mkenums",
                    "GSettings did not select native glib-mkenums")
            require(values["MESON_CROSS.emberbsd_gi_cross"] == "true", "Missing GI cross property")
            require("target-query.py" in environment.get("GI_CROSS_LAUNCHER", ""),
                    "Missing real target query launcher")
            require("gobject-introspection>=" in values["TOOL_DEPENDS"], "Missing native GI tool")
            allowed = {name + " must name an existing absolute file without shell metacharacters"
                       for name in ("EMBERBSD_CROSS_BUILD_PYTHON", "EMBERBSD_GI_QUERY_CONFIG", "EMBERBSD_CROSS_BUILD_CC")}
            allowed.add("EMBERBSD_SDK_SOURCE must name an absolute SDK source directory without shell metacharacters")
            require(set(errors) <= allowed, "Unexpected GI prerequisite failure: " + repr(errors))
        else:
            require("GI_CROSS_LAUNCHER" not in environment and not errors,
                    "Native GSettings selected the cross runner or failed prerequisites")
    else:
        require(recipe == "www/libproxy", "Unknown recipe")
        require(values["PKGNAME"] == "libproxy-0.5.12nb7", "Wrong libproxy identity")
        require(not introspection, "The complete toolkit changed libproxy GI defaults")
        for name in ("lib/girepository-1.0/Libproxy-1.0.typelib", "share/gir-1.0/Libproxy-1.0.gir"):
            require(name in plist.splitlines(), "Missing unconditional binding: " + name)
        selected = set(values["PKG_OPTIONS"].split())
        require(selected <= {"doc", "vala"}, "Unexpected libproxy option")
        expected_options = ["-Ddocs=" + str("doc" in selected).lower(),
                            "-Dvapi=" + str("vala" in selected).lower()]
        compiler_options = ("-Dc_args=", "-Dc_link_args=", "-Dcpp_args=", "-Dcpp_link_args=")
        feature_options = [value for value in options if not value.startswith(compiler_options)]
        require(feature_options == expected_options, "Libproxy changed optional data or runtime backends")
        for name in ("doc", "vala"):
            require((values["PLIST." + name] == "yes") == (name in selected),
                    "Libproxy optional PLIST differs: " + name)
        if cross:
            require(values["MESON_CROSS.emberbsd_gi_cross"] == "true", "Missing libproxy GI cross property")
            require("target-query.py" in environment.get("GI_CROSS_LAUNCHER", ""),
                    "Missing libproxy target query launcher")
            require("gobject-introspection>=" in values["TOOL_DEPENDS"], "Missing libproxy native GI tool")
            allowed = {name + " must name an existing absolute file without shell metacharacters"
                       for name in ("EMBERBSD_CROSS_BUILD_PYTHON", "EMBERBSD_GI_QUERY_CONFIG", "EMBERBSD_CROSS_BUILD_CC")}
            allowed.add("EMBERBSD_SDK_SOURCE must name an absolute SDK source directory without shell metacharacters")
            require(set(errors) <= allowed, "Unexpected libproxy prerequisite failure: " + repr(errors))
        else:
            require("GI_CROSS_LAUNCHER" not in environment and not errors,
                    "Native libproxy selected the cross runner or failed prerequisites")
    return errors


def copy_canonical_recipe(ports, fixture, recipe, hash_file):
    rows = (ports / "pkgsrc/replaces").read_text().splitlines()
    require(rows.count(recipe) == 1, "Expected one canonical replacement: " + recipe)
    owner = ports / "pkgsrc" / recipe
    require((owner / "Makefile").is_file(), "Missing canonical recipe: " + recipe)
    names = tuple(sorted(str(p.relative_to(owner)) for p in owner.rglob("*") if p.is_file()))
    require({"Makefile", "PLIST", "distinfo", "buildlink3.mk", "options.mk"} <= set(names),
            "Incomplete canonical recipe: " + recipe)
    shutil.rmtree(fixture / recipe)
    shutil.copytree(owner, fixture / recipe)
    return {name: hash_file(owner / name) for name in names}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True)
    parser.add_argument("--bmake", required=True)
    parser.add_argument("--sdk-source", required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    ports = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(ports / "profiles/development-toolchain/runtime/recipe/files"))
    import sdk_source
    sdk_source.load(args.sdk_source)
    sdk_source.install_signal_handlers()
    from emberbsd_sdk.process import capture
    from emberbsd_sdk.inventory import hash_file
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
    work = args.work.absolute()
    require(not work.exists() and not work.is_symlink(), "Select a new work directory")
    prepared = args.pkgsrc.resolve(strict=True)
    makeconf = args.makeconf.resolve(strict=True)
    work.mkdir(parents=True)
    fixture = work / "pkgsrc"
    fixture.mkdir()
    receipt = {"scope": "source-composition-and-metadata-only", "commands": [], "queries": [],
               "patches": {}, "canonical_recipes": {},
               "makeconf_sha256": hash_file(makeconf), "status": "running"}

    def run(argv, **kwargs):
        receipt["commands"].append(argv)
        result = capture(argv, **kwargs)
        return result.stdout

    code = 0
    try:
        archive = work / "recipes.tar"
        archive.write_bytes(run(["git", "-C", str(ports / "upstream/pkgsrc"), "archive", "HEAD",
                                 *RECIPES, "www/curl"]))
        run(["tar", "-xf", str(archive), "-C", str(fixture)])
        receipt["canonical_recipes"]["sysutils/libnotify"] = copy_canonical_recipe(
            ports, fixture, "sysutils/libnotify", hash_file)
        for relative in ("profiles/common-build-tools/patches/pkgsrc-curl-security.patch",
                         "profiles/common-graphics/cross/gsettings-desktop-schemas-cross-gir.patch",
                         "profiles/common-graphics/cross/libproxy-cross-disable-introspection.patch",
                         "probes/plasma-mobile/toolkit/libproxy-cross.patch",
                         "probes/plasma-mobile/toolkit/current-network-deps.patch"):
            patch = ports / relative
            receipt["patches"][relative] = hash_file(patch)
            run(["patch", "-f", "-N", "-F", "0", "-p1", "-d", str(fixture)], input=patch.read_bytes())
        for recipe in RECIPES:
            names = ("Makefile", "PLIST")
            if recipe == "sysutils/libnotify":
                names = tuple(receipt["canonical_recipes"][recipe])
                prepared_names = tuple(sorted(str(p.relative_to(prepared / recipe))
                                              for p in (prepared / recipe).rglob("*") if p.is_file()))
                require(prepared_names == names, "Prepared canonical recipe inventory differs: " + recipe)
            if recipe == "www/libproxy":
                names = tuple(sorted(str(p.relative_to(fixture / recipe))
                                     for p in (fixture / recipe).rglob("*")
                                     if p.is_file() and not p.name.endswith((".orig", ".rej"))))
            for name in names:
                require((fixture / recipe / name).read_bytes() == (prepared / recipe / name).read_bytes(),
                        "Prepared recipe differs from patch composition: " + recipe + "/" + name)
            modes = (("yes", None), ("no", None))
            if recipe == "www/libproxy":
                modes += (("yes", "-doc -vala"), ("no", "-doc -vala"))
            for mode, package_options in modes:
                argv = [args.bmake, "-C", str(prepared / recipe), "_MAKEVARS_MK=defined",
                        "_PKGSRC_BARRIER=yes", "USE_CROSS_COMPILE=" + mode]
                if package_options is not None:
                    argv.append("PKG_OPTIONS.libproxy=" + package_options)
                for key in KEYS:
                    argv.extend(("-v", key))
                lines = run(argv, env={**os.environ, "MAKECONF": str(makeconf)}).decode().splitlines()
                require(len(lines) == len(KEYS), "Unexpected bmake response length")
                values = dict(zip(KEYS, lines))
                missing = check_metadata(recipe, mode, values, (prepared / recipe / "PLIST").read_text())
                receipt["queries"].append({"recipe": recipe, "cross": mode, "package_options": package_options, "values": values,
                                           "missing_prerequisites": missing})
        receipt["status"] = "source-composition-and-native-cross-metadata-pass"
    except CommandError as error:
        code = error.returncode
        receipt.update(status="command-failed", error=str(error),
                       stdout=error.stdout.decode(errors="replace"), stderr=error.stderr.decode(errors="replace"))
    except (ProcessOwnershipError, ValueError) as error:
        code = 1
        receipt.update(status="failed", error=str(error))
    finally:
        (work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["status"])
    return code


if __name__ == "__main__":
    sys.exit(main())
