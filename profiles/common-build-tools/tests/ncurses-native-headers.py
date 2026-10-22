#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check real ncurses cross build headers.
"""Use a Darwin host, a configured target source tree and installed tools."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import shutil
import subprocess
import sys
import tarfile


def sha(path, algorithm="sha256"):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def main():
    if len(sys.argv) != 5 or sys.platform != "darwin":
        raise SystemExit("Usage on Darwin: ncurses-native-headers.py PKGSRC MAKECONF TARGET_WRKSRC NEW_WORK")
    tree, conf, target = (Path(p).resolve(strict=True) for p in sys.argv[1:4])
    work = Path(sys.argv[4])
    if not work.is_absolute() or work.exists() or work.is_symlink():
        raise SystemExit("Use a new absolute output directory")
    work.mkdir()
    (work / "tmp").mkdir()
    commands = []
    protected = [target / name for name in ["config.log", "include/ncurses_cfg.h", "include/curses.h", "include/ncurses_dll.h", "ncurses/build.priv.h", "ncurses/names.c", "ncurses/keys.list", "ncurses/tinfo/make_hash.c", "ncurses/tinfo/make_keys.c"]]
    inputs = {str(p): sha(p) for p in protected + [conf, tree / "devel/ncurses/Makefile", tree / "devel/ncurses/distinfo"]}
    base_env = dict(os.environ, TMPDIR=str(work / "tmp"), TMP=str(work / "tmp"), TEMP=str(work / "tmp"), LC_ALL="C")

    def run(label, argv, cwd=work, env=base_env, data=None, success=True):
        outpath, errpath = work / (label + ".stdout"), work / (label + ".stderr")
        with outpath.open("wb") as out, errpath.open("wb") as err:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
            try:
                process.communicate(data)
            except BaseException:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait()
                raise
        record = dict(name=label, argv=argv, cwd=str(cwd), exit=process.returncode)
        commands.append(record)
        (work / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if success and process.returncode:
            raise RuntimeError(f"{label} failed: {errpath.read_text()}")
        return process.returncode, outpath.read_bytes(), errpath.read_bytes()

    make = os.environ.get("BMAKE", "bmake")
    cross = work / "cross"
    cross.mkdir()
    common = [make, "-C", str(tree / "devel/ncurses"), "MAKECONF=" + str(conf), "USE_CROSS_COMPILE=yes", "WRKDIR=" + str(cross), "MAKE_JOBS=2"]
    names = ["PKG_FAIL_REASON", "NATIVE_CC", "NATIVE_CXX", "CCPATH", "DISTDIR", "DISTNAME"]
    _, output, _ = run("cross-metadata", common + sum((["-v", n] for n in names), []))
    values = output.decode().splitlines()
    assert len(values) == len(names)
    meta = dict(zip(names, values))
    assert not meta["PKG_FAIL_REASON"]
    assert meta["DISTNAME"] == "ncurses-6.6"
    # Refuse dependency installation before the recursive configure target.
    native_args = [make, "-C", str(tree / "devel/ncurses"), "MAKECONF=" + str(conf), "USE_CROSS_COMPILE=no"]
    native_names = ["PKG_INFO", "TOOL_DEPENDS", "BUILD_DEPENDS", "DEPENDS", "BOOTSTRAP_DEPENDS", "CONFIGURE_ENV"]
    _, output, _ = run("native-metadata", native_args + sum((["-v", n] for n in native_names), []))
    native_values = output.decode().splitlines()
    assert len(native_values) == len(native_names)
    native_meta = dict(zip(native_names, native_values))
    assert "NCURSES_BUILD_HEADERS" not in native_meta["CONFIGURE_ENV"]
    for kind in native_names[1:5]:
        for index, spec in enumerate(native_meta[kind].split()):
            pattern = spec.split(":", 1)[0]
            run(f"native-{kind}-{index}", shlex.split(native_meta["PKG_INFO"]) + ["-e", pattern])
    package = tree / "devel/ncurses"
    archive = Path(meta["DISTDIR"]) / (meta["DISTNAME"] + ".tar.gz")
    distinfo = (package / "distinfo").read_text()
    expected = re.search(r"^SHA512 \(ncurses-6.6.tar.gz\) = (\w+)$", distinfo, re.M).group(1)
    assert sha(archive, "sha512") == expected
    with tarfile.open(archive) as source:
        source.extractall(cross, filter="data")
    for index, patch in enumerate(sorted((package / "patches").glob("patch-*"))):
        run(f"outer-source-patch-{index}", ["patch", "-p0", "-i", str(patch)], cwd=cross / meta["DISTNAME"])
        inputs[str(patch)] = sha(patch)
    (cross / "config.cache").write_text("ac_cv_header_malloc_h=yes\n")
    (cross / meta["DISTNAME"] / "config.cache").write_text("ac_cv_header_malloc_h=yes\n")
    site = work / "poison.site"
    site.write_text("echo target-config-site-leaked >&2\nac_cv_header_malloc_h=yes\n")
    poisoned = dict(base_env, MAKEFLAGS="OPSYS=NetBSD OS_VERSION=11.0 CC=" + meta["CCPATH"], OPSYS="NetBSD", CC=meta["CCPATH"], ac_cv_header_malloc_h="yes", CONFIG_SITE=str(site))
    _, output, error = run("canonical-pre-configure", common + ["pre-configure"], env=poisoned)
    assert b"target-config-site-leaked" not in output + error
    assert b"NOT found" not in output + error
    assert b"Installing binary package" not in output + error
    native = cross / "native-config/devel/ncurses/work" / meta["DISTNAME"]
    for original, private in [("ncurses_dll.h", "ncurses-build-dll.h"), ("ncurses_cfg.h", "ncurses-build-cfg.h"), ("curses.h", "ncurses-build-curses.h")]:
        assert (native / "include" / original).read_bytes() == (native / "include" / private).read_bytes()
    cfg = (native / "include/ncurses-build-cfg.h").read_text()
    assert '#define SYSTEM_NAME "darwin' in cfg
    assert "#define HAVE_ALLOCA_H 1" in cfg
    assert "#define HAVE_MALLOC_H 1" not in cfg
    log = (native / "config.log").read_text()
    assert meta["CCPATH"] not in log and "--sysroot=" not in log
    assert "target-config-site-leaked" not in log
    flags_text = (native / "ncurses/Makefile").read_text()
    flags = {n: re.search(r"^" + n + r"[ \t]*=[ \t]*(.*)$", flags_text, re.M).group(1) for n in ["CPPFLAGS", "CFLAGS", "LDFLAGS", "LIBS"]}
    assert "-Wno-error" not in flags["CFLAGS"]
    capture = work / "capture-env.py"
    capture.write_text('import json, os\nprint(json.dumps({n: os.environ[n] for n in ["BUILD_CC", "BUILD_CPPFLAGS", "BUILD_CFLAGS", "BUILD_LDFLAGS", "BUILD_LIBS"]}))\n')
    probe = work / "capture-env.mk"
    probe.write_text('.include "${.CURDIR}/Makefile"\n.PHONY: emberbsd-host-env\nemberbsd-host-env:\n\t${RUN}${SETENV} ${CONFIGURE_ENV} ${EMBER_PYTHON:Q} ${EMBER_CAPTURE:Q}\n')
    env_command = common + ["-f", str(probe), "EMBER_PYTHON=" + sys.executable, "EMBER_CAPTURE=" + str(capture), "emberbsd-host-env"]
    _, output, _ = run("actual-configure-env", env_command)
    build = json.loads(output)
    assert build["BUILD_CC"] == meta["NATIVE_CC"]
    assert shlex.split(build["BUILD_CPPFLAGS"]) == ["-DNCURSES_BUILD_HEADERS", "-I" + str(native / "include")] + shlex.split(flags["CPPFLAGS"])
    for field, key in [("BUILD_CFLAGS", "CFLAGS"), ("BUILD_LDFLAGS", "LDFLAGS"), ("BUILD_LIBS", "LIBS")]:
        assert shlex.split(build[field]) == shlex.split(flags[key])
    status, _, error = run("missing-configure-env", env_command[:-1] + ["CONFIGURE_ENV=", "emberbsd-host-env"], success=False)
    assert status and b"BUILD_CC" in error
    # Keep the production target-first include order. Change only an owned
    # copy of the target build header. All other target inputs stay exact.
    overlay = work / "target-overlay"
    (overlay / "ncurses").mkdir(parents=True)
    (overlay / "include").symlink_to(target / "include", target_is_directory=True)
    for entry in (target / "ncurses").iterdir():
        dest = overlay / "ncurses" / entry.name
        if entry.name == "build.priv.h":
            shutil.copy2(entry, dest)
        else:
            dest.symlink_to(entry, target_is_directory=entry.is_dir())
    role_header = overlay / "ncurses/build.priv.h"
    original_header = role_header.read_bytes()
    run("target-build-header-patch", ["patch", "-p0", "-i", str(package / "patches/patch-ncurses_build.priv.h")], cwd=overlay)
    patched_header = role_header.read_bytes()
    assert original_header != patched_header
    fixed = ["-DHAVE_CONFIG_H", "-DUSE_BUILD_CC", "-I" + str(overlay / "ncurses"), "-I" + str(overlay / "include")]
    compiler = shlex.split(build["BUILD_CC"])
    normal = ["-DUSE_BUILD_CC", "-I" + str(native / "ncurses"), "-I" + str(native / "include")] + shlex.split(flags["CPPFLAGS"])
    candidate = fixed + shlex.split(build["BUILD_CPPFLAGS"])
    common_flags = shlex.split(build["BUILD_CFLAGS"])
    link = shlex.split(build["BUILD_LDFLAGS"]) + shlex.split(build["BUILD_LIBS"])
    binaries = {}
    for name in ["make_hash", "make_keys"]:
        source = str(target / "ncurses/tinfo" / (name + ".c"))
        status, _, error = run("baseline-" + name, compiler + fixed + [source, "-o", str(work / ("baseline-" + name))], cwd=overlay / "ncurses", success=False)
        assert status and b"malloc.h" in error
        for label, includes in [("native", normal), ("candidate", candidate)]:
            binary = work / (label + "-" + name)
            args = compiler + includes + common_flags + [source] + link + ["-o", str(binary)]
            run(label + "-" + name, args, cwd=overlay / "ncurses")
            binaries[label, name] = binary
            run(label + "-usage-" + name, [str(binary), "-?"], cwd=overlay / "ncurses")
        _, _, trace = run("include-trace-" + name, compiler + candidate + common_flags + ["-H", "-fsyntax-only", source], cwd=overlay / "ncurses")
        for private in ["ncurses-build-dll.h", "ncurses-build-cfg.h", "ncurses-build-curses.h"]:
            assert str(native / "include" / private).encode() in trace
        dumps = []
        for label, includes in [("native", normal), ("candidate", candidate)]:
            _, macros, _ = run(label + "-macros-" + name, compiler + includes + common_flags + ["-dM", "-E", source], cwd=overlay / "ncurses")
            active = set(macros.decode().splitlines())
            active.discard("#define NCURSES_BUILD_HEADERS 1")
            dumps.append(active)
        assert dumps[0] == dumps[1], sorted(dumps[0] ^ dumps[1])
        assert any(line.startswith('#define SYSTEM_NAME "darwin') for line in dumps[1])
        assert "#define HAVE_MALLOC_H 1" not in dumps[1]
    caps = (target / "include/Caps").read_bytes() + (target / "include/Caps-ncurses").read_bytes()
    for column, root in [(1, "info"), (3, "cap"), (1, "user")]:
        results = []
        for label in ["native", "candidate"]:
            _, output, _ = run(f"{label}-table-{root}", [str(binaries[label, "make_hash"]), str(column), root, "1"], data=caps)
            assert output
            results.append(output)
        assert results[0] == results[1]
    results = [run(label + "-key-table", [str(binaries[label, "make_keys"]), str(target / "ncurses/keys.list")])[1] for label in ["native", "candidate"]]
    assert results[0] and results[0] == results[1]
    role_header.write_bytes(original_header)
    try:
        for name in ["make_hash", "make_keys"]:
            status, _, error = run("missing-role-guard-" + name, compiler + candidate + common_flags + ["-fsyntax-only", str(target / "ncurses/tinfo" / (name + ".c"))], cwd=overlay / "ncurses", success=False)
            assert status and b"malloc.h" in error
    finally:
        role_header.write_bytes(patched_header)
    private = native / "include/ncurses-build-cfg.h"
    hidden = native / "include/ncurses-build-cfg.h.hidden"
    private.rename(hidden)
    try:
        status, _, error = run("missing-private-config", compiler + candidate + common_flags + ["-fsyntax-only", str(target / "ncurses/tinfo/make_hash.c")], cwd=overlay / "ncurses", success=False)
        assert status and b"ncurses-build-cfg.h" in error
    finally:
        hidden.rename(private)
    for path, digest in inputs.items():
        assert sha(Path(path)) == digest, path
    (work / "result.json").write_text(json.dumps(dict(inputs=inputs, metadata=meta, native_flags=flags, actual_configure_env=build, target_overlay_header_sha256=sha(role_header), target_original_header_sha256=hashlib.sha256(original_header).hexdigest(), archive_sha512=expected, scope="Actual canonical native header configure and real host generators. No target package build, target runtime, package registration or whole-library acceptance."), indent=2) + "\n")
    print("PASS: canonical native headers, polluted outer cache isolation, real generator outputs, target-first include trace, missing-role-guard and absent-private-header refusal and unchanged target inputs")


if __name__ == "__main__":
    main()
