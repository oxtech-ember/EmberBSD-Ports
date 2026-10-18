#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real Boost/pkgsrc cross target regression.
"""Check native b2 roles, target metadata and actual Boost.Context selection."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import sys
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sdk-source", "pkgsrc", "archive", "source", "native-makeconf", "cross-makeconf", "bmake", "b2", "cxx", "ar", "readelf", "work"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15) or sys.platform != "linux":
        parser.error("This regression requires the qualified Linux/Python 3.15 host.")
    sdk = Path(args.sdk_source).resolve(strict=True)
    sys.path.insert(0, str(sdk / "src"))
    import emberbsd_sdk
    from emberbsd_sdk import inventory, jsonio, paths, process
    from emberbsd_sdk.errors import CommandError
    if emberbsd_sdk.API_VERSION != 1:
        parser.error("SDK library API 1 is required.")
    root = Path(__file__).resolve().parents[3]
    pkgsrc = Path(args.pkgsrc).resolve(strict=True)
    source = Path(args.source).resolve(strict=True)
    archive = Path(args.archive).resolve(strict=True)
    work = Path(paths.canonical_new(args.work))
    for item in (pkgsrc, source, sdk):
        paths.reject_overlap(str(work), str(item))
    if inventory.sha256_file(archive) != "5c1d40cb8e19adbf740a4ec2da35b3e58f3f5804b1dce44deb53df72193cbc6c":
        parser.error("The pinned Boost 1.92.0 archive hash differs.")
    tools = {key: Path(getattr(args, key)).resolve(strict=True) for key in ("bmake", "b2", "cxx", "ar", "readelf")}
    configs = {key: Path(getattr(args, key + "_makeconf")).resolve(strict=True) for key in ("native", "cross")}
    work.mkdir()
    commands = []

    def run(label, argv, *, cwd=work, data=None, expected=0):
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
        if status != expected:
            raise SystemExit(f"Unexpected result for {label}: {status}; inspect {work}.")
        return stdout.decode("utf-8")

    assert run("compiler-version", [tools["cxx"], "-dumpfullversion"]).strip() == "16.2.0"
    assert run("compiler-target", [tools["cxx"], "-dumpmachine"]).strip() == "aarch64--netbsd"
    assert "B2 5.5.3 (OS=LINUX" in run("native-engine", [tools["b2"], "-v"])
    patch = root / "profiles/common-build-tools/patches/pkgsrc-boost-cross-target.patch"
    delta = patch.read_bytes()
    baseline = work / "baseline"
    selected = ("devel/boost-jam", "devel/boost-libs")
    original = {
        "devel/boost-jam/bjam.mk": "2ce3d42f4277468b6b94a6fdab49a2cf8b4084fa14060bd65b913a8969feb054",
        "devel/boost-libs/Makefile": "f522b1f5f41a20928ce267fb9e06b278d513e015cfb4940bbd6366de731ed9cf",
        "devel/boost-libs/buildlink3.mk": "95fa8862a26d9c67ed391b7d8d51ca87f21b09e8bb862562371d9dac4a066763",
    }
    for name in selected:
        shutil.copytree(pkgsrc / name, baseline / name)
    if any(inventory.sha256_file(baseline / name) != digest for name, digest in original.items()):
        run("reverse-current-recipe", ["patch", "-R", "-f", "--fuzz=0", "-p1", "-d", baseline], data=delta)
    assert all(inventory.sha256_file(baseline / name) == digest for name, digest in original.items())
    # The complete Plasma overlay must use this same repair. It must not
    # retain a second compiler configuration or a hardcoded ARM target.
    for name in ("Makefile", "buildlink3.mk"):
        shared = baseline / "devel/boost-libs" / name
        toolkit = root / "probes/plasma-mobile/toolkit/recipes/devel/boost-libs" / name
        assert shared.read_bytes() == toolkit.read_bytes(), name
    exporter = (root / "scripts/prepare-pkgsrc.sh").read_text(encoding="utf-8")
    assert exporter.rindex('"$root/profiles/common-build-tools/patches/pkgsrc-boost-cross-target.patch"') > exporter.index('cp -R "$toolkit/recipes/$recipe" "$destination/$recipe"')
    metadata = {}
    for variant in ("before", "after"):
        tree = work / variant
        tree.mkdir()
        for item in pkgsrc.iterdir():
            if item.name != "devel":
                (tree / item.name).symlink_to(item, target_is_directory=item.is_dir())
        (tree / "devel").mkdir()
        for item in (pkgsrc / "devel").iterdir():
            if item.name not in ("boost-jam", "boost-libs"):
                (tree / "devel" / item.name).symlink_to(item, target_is_directory=item.is_dir())
        for name in selected:
            shutil.copytree(baseline / name, tree / name)
        if variant == "after":
            run("apply-recipe", ["patch", "-f", "--fuzz=0", "-p1", "-d", tree], data=delta)
        metadata[variant] = {}
        cases = {
            "native": ("native", []),
            "aarch64": ("cross", ["EMBERBSD_CROSS_TARGET=aarch64"]),
            "amd64": ("cross", ["EMBERBSD_CROSS_TARGET=amd64"]),
            "host-recursion": ("cross", ["USE_CROSS_COMPILE=no"]),
            "unsupported": ("cross", ["MACHINE_ARCH=mips64"]),
        }
        keys = ("BJAM_ARGS", "BJAM_BUILD", "CXX", "AR", "TOOL_DEPENDS", "PLIST.context", "PLIST.fiber", "PLIST.log", "PKG_FAIL_REASON", "WRKDIR")
        for case, (config, extra) in cases.items():
            argv = [tools["bmake"], "MAKECONF=" + str(configs[config]), "WRKOBJDIR=" + str(work / "objects" / variant / case), "MAKE_JOBS=1", *extra]
            # Expanded -V expressions also enter .MAKEFLAGS. A value that
            # contains b2's -j option can falsely trip pkgsrc's own -j guard.
            lines = run(variant + "-" + case, [*argv, *(arg for key in keys for arg in ("-v", key))], cwd=tree / "devel/boost-libs").splitlines()
            assert len(lines) == len(keys)
            value = dict(zip(keys, lines))
            metadata[variant][case] = value
            if variant == "after" and case in ("aarch64", "amd64"):
                flags = shlex.split(value["BJAM_BUILD"])
                wanted = {"target-os=netbsd", "address-model=64", "binary-format=elf"}
                wanted.update(("architecture=arm", "abi=aapcs") if case == "aarch64" else ("architecture=x86", "abi=sysv"))
                assert wanted.issubset(flags)
                assert "--site-config=" + value["WRKDIR"] + "/pkgsrc-cross-site-config.jam" in shlex.split(value["BJAM_ARGS"])
                assert value["PLIST.context"] == value["PLIST.fiber"] == value["PLIST.log"] == "yes"
            if variant == "after" and case == "unsupported":
                assert "aarch64 or x86_64 target metadata" in value["PKG_FAIL_REASON"]
            if case in ("native", "host-recursion"):
                assert "target-os=netbsd" not in shlex.split(value["BJAM_BUILD"])
            if case in ("native", "aarch64", "host-recursion"):
                assert not value["PKG_FAIL_REASON"], (variant, case, value["PKG_FAIL_REASON"])
        # Run the actual make target. A successful metadata query alone must
        # not hide a malformed Jam configuration or shell redirection.
        config = metadata[variant]["aarch64"]
        Path(config["WRKDIR"]).mkdir(parents=True)
        run(variant + "-pre-build", [tools["bmake"], "MAKECONF=" + str(configs["cross"]),
            "WRKOBJDIR=" + str(work / "objects" / variant / "aarch64"), "pre-build"], cwd=tree / "devel/boost-libs")
        if variant == "after":
            generated = Path(config["WRKDIR"]) / "pkgsrc-cross-site-config.jam"
            assert generated.read_text(encoding="utf-8") == "using gcc : : " + config["CXX"] + " : <archiver>" + config["AR"] + " ;\n"
    for case in ("native", "host-recursion"):
        before, after = (metadata[v][case] for v in ("before", "after"))
        assert before["BJAM_BUILD"] == after["BJAM_BUILD"]
        for key in ("CXX", "AR", "TOOL_DEPENDS", "PLIST.context", "PLIST.fiber", "PLIST.log", "PKG_FAIL_REASON"):
            assert before[key] == after[key], (case, key)
    # Source identities cover the actual architecture aliases and assembly.
    checked = ["libs/context/build/Jamfile.v2", "libs/context/boost-context-features.jam"]
    checked += ["libs/context/src/asm/" + name + "_arm64_aapcs_elf_gas.S" for name in ("make", "jump", "ontop")]
    remaining = {"boost_1_92_0/" + name: name for name in checked}
    with tarfile.open(archive, mode="r|bz2") as upstream:
        for member in upstream:
            name = remaining.pop(member.name, None)
            if name is not None:
                assert member.isfile(), name
                assert (source / name).read_bytes() == upstream.extractfile(member).read(), name
                if not remaining:
                    break
    assert not remaining, remaining
    macros = run("target-header-macros", [tools["cxx"], "-I" + str(source), "-dM", "-E", "-x", "c++", "-include", "boost/config.hpp", "-include", "boost/predef/os.h", "/dev/null"])
    for wanted in ('#define BOOST_PLATFORM "NetBSD " BOOST_STRINGIZE(__NetBSD__)',
                   '#define BOOST_OS_BSD_NET BOOST_VERSION_NUMBER_AVAILABLE',
                   '#define __aarch64__ 1', '#define __GNUC__ 16'):
        assert wanted in macros, wanted
    site = work / "source-site-config.jam"
    site.write_text(f'using gcc : : "{tools["cxx"]}" : <archiver>"{tools["ar"]}" ;\n', encoding="utf-8")
    source_graphs = {}
    for variant in ("before", "after"):
        flags = shlex.split(metadata[variant]["aarch64"]["BJAM_BUILD"])
        graph = run(variant + "-source-graph", [tools["b2"], "--site-config=" + str(site), "--user-config=", "--debug-building", "--with-context", "--layout=system", "--build-dir=" + str(work / (variant + "-graph")), "-j1", "-n", "-a", "-d2", *flags, "stage"], cwd=source)
        source_graphs[variant] = graph
        assert ("<target-os>linux" if variant == "before" else "<target-os>netbsd") in graph
        for name in ("make", "jump", "ontop"):
            assert name + "_arm64_aapcs_elf_gas.S" in graph
        assert "libboost_context.so.1.92.0" in graph and "libboost_context.a" in graph
        assert (" -lrt " in graph) == (variant == "before")
    # Compile the upstream assembly with the selected target GCC. This is
    # object/ABI evidence, not a package or target execution result.
    for name in ("make", "jump", "ontop"):
        assembly = source / "libs/context/src/asm" / (name + "_arm64_aapcs_elf_gas.S")
        obj = work / (name + ".o")
        run("compile-" + name, [tools["cxx"], "-x", "assembler-with-cpp", "-fPIC", "-O2", "-c", assembly, "-o", obj])
        header = run("elf-" + name, [tools["readelf"], "-h", obj])
        assert "AArch64" in header and "REL (Relocatable file)" in header
    jsonio.write_json(work / "result.json", dict(status="PASS", sdk_api=1,
        scope="Actual native/cross pkgsrc metadata, real b2 Context graphs and three GCC16 AArch64 assembly objects. Full target libraries and execution remain pending.",
        metadata=metadata, inputs={str(p): inventory.sha256_file(p) for p in (archive, patch, Path(__file__).resolve(), *(source / name for name in checked))}))
    print("PASS: native/host roles, NetBSD ARM64/amd64 metadata, unsupported target refusal, common toolkit provider, real target headers/Context selection and three GCC16 AArch64 objects.")


if __name__ == "__main__":
    main()
