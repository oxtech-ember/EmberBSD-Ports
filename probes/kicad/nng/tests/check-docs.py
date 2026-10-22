#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Use the actual upstream CMake docs module.
"""Check requested documentation refusal and real Asciidoctor output."""
import argparse
from pathlib import Path
import shutil
import subprocess


def run(command, log, success=True):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
    log.write_text(result.stdout)
    if (result.returncode == 0) != success:
        raise RuntimeError(f"Unexpected status {result.returncode}: {command}; see {log}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--cmake", type=Path, required=True)
    parser.add_argument("--asciidoctor", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    source = args.source.resolve()
    module = source / "docs/man/CMakeLists.txt"
    assert 'message(WARNING "Could not find asciidoctor: skipping docs")' in module.read_text()
    candidate = args.work / "candidate-man"
    shutil.copytree(module.parent, candidate)
    delta = Path(__file__).resolve().parents[1] / "patches/docs-required.patch"
    patchroot = args.work / "patch-source/docs"
    patchroot.mkdir(parents=True)
    (patchroot / "man").symlink_to(candidate)
    run(["patch", "-p1", "-F", "0", "-d", str(patchroot.parent), "-i", str(delta)],
        args.work / "patch.log")
    for name, docs, enabled, formatter, success in [
        ("upstream-missing", module.parent, True, None, True),
        ("candidate-missing", candidate, True, None, False),
        ("candidate-disabled", candidate, False, None, True),
        ("candidate-real", candidate, True, args.asciidoctor.resolve(), True),
    ]:
        project = args.work / name
        project.mkdir()
        (project / "CMakeLists.txt").write_text(
            'cmake_minimum_required(VERSION 3.20)\nproject(NNGDocs NONE)\n'
            'set(CMAKE_INSTALL_DOCDIR share/doc/nng)\n'
            'set(CMAKE_INSTALL_MANDIR man)\n'
            f'add_subdirectory("{docs}" docs)\n')
        command = [str(args.cmake), "-S", str(project), "-B", str(project / "build"),
                   "-G", "Unix Makefiles", "-DCMAKE_MAKE_PROGRAM=/usr/bin/make",
                   f"-DNNG_ENABLE_DOC:BOOL={'ON' if enabled else 'OFF'}",
                   "-DCMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH=FALSE",
                   "-DCMAKE_FIND_USE_CMAKE_SYSTEM_PATH=FALSE",
                   "-DCMAKE_FIND_USE_CMAKE_ENVIRONMENT_PATH=FALSE"]
        if formatter:
            command.append(f"-DASCIIDOCTOR:FILEPATH={formatter}")
        output = run(command, args.work / f"{name}.log", success)
        if name == "upstream-missing":
            assert "skipping docs" in output
        if name == "candidate-missing":
            assert "NNG_ENABLE_DOC requires asciidoctor" in output
        if formatter:
            for target, output in [("man", "nngcat.1"), ("html", "nngcat.1.html")]:
                run(["/usr/bin/make", "-C", str(project / "build"),
                     "-f", f"docs/CMakeFiles/{target}.dir/build.make", f"docs/{output}"],
                    args.work / f"real-{target}.log")
            man = (project / "build/docs/nngcat.1").read_text()
            html = (project / "build/docs/nngcat.1.html").read_text()
            assert '.TH "NNGCAT" "1"' in man
            assert "<!DOCTYPE html>" in html and "nngcat" in html
        print(f"PASS: {name}")


if __name__ == "__main__":
    main()
