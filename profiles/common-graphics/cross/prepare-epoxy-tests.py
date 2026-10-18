#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed libepoxy consumer acceptance.
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile


# Exact currently accepted package; changing it requires matching Mesa acceptance.
MESA_PACKAGE = "MesaLib-26.2.4nb9"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def hash_manifest(manifest):
    result = {}
    for line in manifest.read_text().splitlines():
        fields = line.split("  ", 1)
        if (len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None
                or not fields[1] or ".." in PurePosixPath(fields[1]).parts or fields[1] in result):
            raise SystemExit("invalid input manifest")
        result[fields[1]] = fields[0]
    if not result:
        raise SystemExit("empty input manifest")
    return result


def verify_manifest(base, manifest):
    entries = hash_manifest(manifest)
    for name, expected in entries.items():
        actual = base / name
        if not actual.is_file() or digest(actual) != expected:
            raise SystemExit(f"input drift: {actual}")
    return entries


def main():
    if len(sys.argv) != 8:
        raise SystemExit("usage: prepare-epoxy-tests.py CROSS_TOOLS SYSROOT EPOXY_BUILD EPOXY_PACKAGE MESA_METADATA_BUNDLE EPOXY_CONSUMER_WORK NEW_WORK")
    tools, sysroot, build, package, mesa, consumer = (Path(arg).resolve(strict=True) for arg in sys.argv[1:7])
    work = Path(sys.argv[7])
    if not work.is_absolute() or work.exists() or work.is_symlink():
        raise SystemExit("NEW_WORK must be new and absolute")
    owner = Path(__file__).resolve().parent
    readelf = tools / "bin/aarch64--netbsd-readelf"
    mesa_entries = verify_manifest(mesa, mesa / "artifacts.sha256")
    consumer_entries = verify_manifest(consumer, consumer / "inputs.sha256")
    result = subprocess.run(["sh", str(mesa / "run-mesa-package-tests.sh"), "--verify-sysroot", str(mesa), str(sysroot)],
                            timeout=300, check=False)
    if result.returncode:
        raise SystemExit("Mesa metadata verification failed")
    mesa_contents = next((mesa / name for name in ("source/MesaLib.CONTENTS", "MesaLib.CONTENTS") if (mesa / name).is_file()), None)
    if (mesa_contents is None or str(mesa_contents.relative_to(mesa)) not in mesa_entries
            or [line for line in mesa_contents.read_text().splitlines() if line.startswith("@name ")] != ["@name " + MESA_PACKAGE]):
        raise SystemExit("require the accepted Mesa package: " + MESA_PACKAGE)
    project = json.loads((build / "meson-info/intro-projectinfo.json").read_text())
    if project.get("version") != "1.5.10":
        raise SystemExit("require actual libepoxy 1.5.10 build")
    consumer_binary = consumer / "epoxy-pkgconfig-render"
    if consumer_entries.get(str(consumer_binary)) != digest(consumer_binary):
        raise SystemExit("consumer executable is not in its input receipt")
    inputs = {str(path): digest(path) for path in (package, consumer / "inputs.sha256", mesa / "artifacts.sha256",
              build / "meson-info/intro-projectinfo.json", build / "meson-info/intro-tests.json", Path(__file__).resolve(),
              owner / "run-epoxy-tests.sh", owner / "mesa-render.c", readelf)}
    bundle = work / "bundle"
    (bundle / "bin").mkdir(parents=True)
    (bundle / "source").mkdir()
    shutil.copy2(consumer_binary, bundle / "bin/epoxy-render")
    shutil.copy2(owner / "run-epoxy-tests.sh", bundle)
    shutil.copy2(owner / "mesa-render.c", bundle / "source")
    for name in ("inputs.sha256", "consumer-build.log.command", "consumer-elf.log"):
        shutil.copy2(consumer / name, bundle / "source")
    files = hash_manifest(mesa / "mesa-package-files.sha256")
    links = dict(line.split("\t", 1) for line in (mesa / "mesa-package-links.tsv").read_text().splitlines())
    runtime = hash_manifest(mesa / "runtime-libraries.sha256")
    seen = set()
    with tarfile.open(package, "r|gz") as archive:
        for entry in archive:
            name = entry.name
            if entry.isdir():
                continue
            if name in seen:
                raise SystemExit("duplicate package entry")
            seen.add(name)
            if name.startswith("+"):
                if name == "+CONTENTS" and entry.isfile():
                    (bundle / "source/libepoxy.CONTENTS").write_bytes(archive.extractfile(entry).read())
                continue
            if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
                raise SystemExit("unsafe package path")
            target = "/usr/pkg/" + name
            path = sysroot / target.removeprefix("/")
            if entry.isfile():
                package_hash = hashlib.file_digest(archive.extractfile(entry), "sha256").hexdigest()
                if not path.is_file() or package_hash != digest(path):
                    raise SystemExit("installed libepoxy drift: " + name)
            elif entry.issym():
                if not path.is_symlink() or os.readlink(path) != entry.linkname:
                    raise SystemExit("installed link drift: " + name)
                links[target] = entry.linkname
            else:
                raise SystemExit("unsupported package entry")
            files[target] = digest(path)
            with path.open("rb") as stream:
                if stream.read(4) == b"\x7fELF":
                    runtime[target] = files[target]
    contents = (bundle / "source/libepoxy.CONTENTS").read_text()
    if ([line for line in contents.splitlines() if line.startswith("@name ")] != ["@name libepoxy-1.5.10nb2"]
            or "@blddep " + MESA_PACKAGE not in contents.splitlines()
            or "@pkgdep MesaLib>=26.2.4nb4" not in contents.splitlines()):
        raise SystemExit("wrong package identity/dependency")
    selected = ("header_guards", "misc_defines", "khronos_typedefs", "gl_version")
    tests = [test for test in json.loads((build / "meson-info/intro-tests.json").read_text()) if test["name"] in selected]
    if sorted(test["name"] for test in tests) != sorted(selected):
        raise SystemExit("missing/duplicate upstream tests")
    rows = []
    for test in tests:
        command = test["cmd"]
        executable = Path(command[0]).resolve(strict=True) if len(command) == 1 and Path(command[0]).is_absolute() else None
        environment = test["env"]
        library_path = Path(environment.get("LD_LIBRARY_PATH", ""))
        library_path = library_path.resolve(strict=True) if library_path.is_absolute() and library_path.is_dir() else None
        # Remove only Meson's one exact build-library override, including valid relocated symlink spellings.
        if (executable is None or not executable.is_relative_to(build) or executable == build
                or list(environment) != ["LD_LIBRARY_PATH"] or library_path != build / "src"
                or test.get("workdir") is not None or test["protocol"] != "exitcode"):
            raise SystemExit("unexpected pure test prerequisites")
        limit = test["timeout"]
        if type(limit) is not int or not 1 <= limit <= 120:
            raise SystemExit("unbounded upstream test")
        inputs[command[0]] = digest(command[0])
        shutil.copy2(command[0], bundle / "bin" / test["name"])
        rows.append((test["name"], limit))
    for path in sorted((bundle / "bin").iterdir()):
        with path.open("rb") as stream:
            header = stream.read(20)
        if len(header) != 20 or header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != 183:
            raise SystemExit("not AArch64 ELF")
        result = subprocess.run([str(readelf), "-d", str(path)], capture_output=True, text=True, timeout=30, check=False)
        if result.returncode:
            raise SystemExit(result.stderr)
        dynamic = result.stdout
        (bundle / "source" / (path.name + ".dynamic")).write_text(dynamic)
        paths = [value for entry in re.findall(r"\((?:RPATH|RUNPATH)\).*\[([^\]]+)\]", dynamic) for value in entry.split(":")]
        if not all(os.path.abspath(value) in ("/usr/pkg/lib", "/usr/pkg/gcc16/lib") for value in paths):
            raise SystemExit("foreign test runtime path")
        for name in re.findall(r"\(NEEDED\).*\[([^\]]+)\]", dynamic):
            if not (any(PurePosixPath(value).name == name for value in runtime)
                    or (sysroot / "usr/lib" / name).is_file() or (sysroot / "lib" / name).is_file()):
                raise SystemExit("unrecorded package test dependency: " + name)
    for name, entries in (("installed-files.sha256", files), ("runtime-libraries.sha256", runtime)):
        (bundle / name).write_text("".join(f"{value}  {path}\n" for path, value in sorted(entries.items())))
    (bundle / "installed-links.tsv").write_text("".join(f"{path}\t{target}\n" for path, target in sorted(links.items())))
    (bundle / "tests.tsv").write_text("".join(f"{name}\t{limit}\n" for name, limit in rows))
    (bundle / "source/upstream-tests.json").write_text(json.dumps(tests, indent=2) + "\n")
    receipt = {"package": str(package), "mesa_package": MESA_PACKAGE, "input_sha256": inputs,
               "python": sys.version, "python_executable": sys.executable,
               "scope": "Four unconditional upstream pure tests plus actual epoxy-dispatched surfaceless rendering. Display-dependent EGL/GLX tests are not included."}
    (bundle / "source/receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    for path, expected in inputs.items():
        if digest(path) != expected:
            raise SystemExit("input changed during preparation")
    verify_manifest(mesa, mesa / "artifacts.sha256")
    verify_manifest(consumer, consumer / "inputs.sha256")
    paths = sorted(path for path in bundle.rglob("*") if path.is_file())
    (bundle / "artifacts.sha256").write_text("".join(f"{digest(path)}  {path.relative_to(bundle)}\n" for path in paths))
    archive = work / "epoxy-tests.tar.gz"
    # stdlib archive writing avoids GNU/BSD tar option differences and copies no xattrs.
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as output:
        output.add(bundle, arcname=".")
    print(f"{digest(archive)}  {archive}")


if __name__ == "__main__":
    main()
