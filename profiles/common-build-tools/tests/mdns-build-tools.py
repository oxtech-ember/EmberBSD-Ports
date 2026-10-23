#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual mDNSResponder make/dependency regression.
"""Check the pinned recipe and source graph without compiling or installing."""
import argparse
import os
from pathlib import Path
import re
import shutil
import sys
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-source", required=True)
    parser.add_argument("--pkgsrc", required=True)
    parser.add_argument("--baseline-recipe", required=True,
                        help="Original net/mDNSResponder/Makefile from the pinned pkgsrc tree")
    parser.add_argument("--archive", required=True)
    parser.add_argument("--makeconf", required=True)
    parser.add_argument("--bmake", default="bmake")
    parser.add_argument("--gmake", default="gmake")
    parser.add_argument("--work", required=True)
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
    archive = Path(args.archive).resolve(strict=True)
    makeconf = Path(args.makeconf).resolve(strict=True)
    work = Path(paths.canonical_new(args.work))
    paths.reject_overlap(str(work), str(pkgsrc))
    if inventory.sha256_file(archive) != "f665cf02b5c930f9b70fb39b7567f03dd821997594c56ce399098eaa0372fb15":
        parser.error("The pinned upstream archive hash differs.")
    bmake = shutil.which(args.bmake)
    gmake = shutil.which(args.gmake)
    if not bmake or not gmake:
        parser.error("Select existing native bmake and GNU make executables.")
    work.mkdir()
    commands = []

    def run(label, argv, *, cwd=work, env=None, data=None):
        argv = [str(a) for a in argv]
        try:
            result = process.capture(argv, cwd=str(cwd), env=env, input=data)
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

    run("bmake-version", [bmake, "-r", "-f", "/dev/null", "-V", "MAKE_VERSION"])
    run("gmake-version", [gmake, "--version"])
    sdk_commit = run("sdk-commit", ["git", "-C", sdk, "rev-parse", "HEAD"]).strip()
    current = root / "pkgsrc/net/mDNSResponder"
    baseline = work / "baseline/net/mDNSResponder"
    baseline.mkdir(parents=True)
    source_recipe = pkgsrc / "net/mDNSResponder"
    shutil.copytree(source_recipe, baseline, dirs_exist_ok=True)
    recipe = Path(args.baseline_recipe).resolve(strict=True)
    original_hash = "5a7d683cb8323c63ab2202011b598d8089e17ca55238862276c9b22d300f96fd"
    if inventory.sha256_file(recipe) != original_hash:
        raise SystemExit("The baseline recipe is not the pinned original.")
    shutil.copy2(recipe, baseline / "Makefile")
    metadata = {}
    for variant in ("before", "after"):
        tree = work / variant
        tree.mkdir()
        for item in pkgsrc.iterdir():
            if item.name != "net":
                (tree / item.name).symlink_to(item, target_is_directory=item.is_dir())
        (tree / "net").mkdir()
        for item in (pkgsrc / "net").iterdir():
            if item.name != "mDNSResponder":
                (tree / "net" / item.name).symlink_to(item, target_is_directory=item.is_dir())
        package = tree / "net/mDNSResponder"
        shutil.copytree(baseline, package)
        if variant == "after":
            shutil.copytree(current, package, dirs_exist_ok=True)
        metadata[variant] = {}
        for system in ("NetBSD", "Linux", "Darwin"):
            # Tool choices are cached in WRKDIR. A shared work path would
            # let the repaired package's cache hide the original dependency.
            config = work / (variant + "-" + system + ".conf")
            config.write_text('.include "' + str(makeconf) + '"\n'
                '.if defined(BSD_PKG_MK)\nWRKOBJDIR=' + str(work / "objects" / (variant + "-" + system)) + '\n.endif\n')
            selected = {}
            for variable in ("USE_TOOLS", "BUILD_DEPENDS", "TOOL_DEPENDS", "MAKE_FLAGS", "BUILDLINK_API_DEPENDS.flex"):
                selected[variable] = run(variant + "-" + system + "-" + variable,
                    [bmake, "MAKECONF=" + str(config), "OPSYS=" + system,
                     "show-var", "VARNAME=" + variable], cwd=package).strip()
            tools = {word.split(":", 1)[0] for word in selected["USE_TOOLS"].split()}
            generators = {"flex", "bison"}.issubset(tools)
            assert generators == (variant == "before" or system == "Darwin")
            if variant == "after" and system == "NetBSD":
                assert not re.search(r"(?:^|\s)(?:flex|bison)[><=]", selected["BUILD_DEPENDS"] + " " + selected["TOOL_DEPENDS"])
                assert selected["BUILDLINK_API_DEPENDS.flex"] == ""
                assert "os=netbsd" in selected["MAKE_FLAGS"].split()
            if variant == "before" and system == "NetBSD":
                assert "flex>=" in selected["BUILDLINK_API_DEPENDS.flex"]
            metadata[variant][system] = selected
    with tarfile.open(archive) as source:
        source.extractall(work / "source", filter="data")
    source = work / "source/mDNSResponder-mDNSResponder-2881.120.11/mDNSPosix"
    # GNU make replaces the recipe's environment value with the build-host OS.
    env = dict(os.environ, os="netbsd")
    before = run("source-host-selection", [gmake, "-n", "objects/prod/PosixDaemon.c.o"], cwd=source, env=env)
    after = run("source-target-selection", [gmake, "-n", "os=netbsd", "all"], cwd=source, env=env)
    darwin = run("source-darwin-generators", [gmake, "-n", "os=x", "all"], cwd=source)
    assert "-DHAVE_LINUX" in before and "-DTARGET_OS_LINUX" in before
    assert "-DHAVE_LINUX" not in after and "-DTARGET_OS_LINUX" not in after
    assert not re.search(r"^(?:flex|bison)\s", after, re.M)
    assert re.search(r"^flex\s", darwin, re.M) and re.search(r"^bison\s", darwin, re.M)
    for name in ("mdnsd", "libdns_sd.so", "dns-sd", "mDNSClientPosix", "mDNSResponderPosix", "mDNSProxyResponderPosix", "mDNSNetMonitor"):
        assert name in after, name
    # Exercise a real generator-dependent target as a control. The NetBSD
    # default graph omits dnsextd; its rules remain intact and still need tools.
    explicit = run("source-explicit-dnsextd", [gmake, "-n", "os=netbsd", "dnsextd"], cwd=source)
    assert re.search(r"^flex\s", explicit, re.M) and re.search(r"^bison\s", explicit, re.M)
    jsonio.write_json(work / "result.json", dict(status="PASS", sdk_api=1, sdk_commit=sdk_commit,
        scope="Actual pkgsrc metadata and upstream GNU make dry runs. No package, target execution or Darwin build acceptance.",
        metadata=metadata, inputs={str(p): inventory.sha256_file(p) for p in
        (archive, recipe, current / "Makefile", current / "distinfo", Path(__file__).resolve(), *(sdk / "src/emberbsd_sdk" / name for name in
        ("__init__.py", "inventory.py", "jsonio.py", "paths.py", "process.py")))}))
    print("PASS: actual dependency baseline, complete NetBSD graph, target OS selection and retained Darwin/explicit generators.")


if __name__ == "__main__":
    main()
