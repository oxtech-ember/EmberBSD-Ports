#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Keep target Qt metadata independent of the build host.
"""Normalize installed Qt metadata for native and cross package roles."""

from pathlib import Path
import os
import re
import shutil
import sys


def fail(message):
    raise SystemExit(message)


def absolute_nonroot(value):
    if not value.startswith("/") or value == "/" or "\n" in value:
        fail("absolute, non-root paths required")
    return Path(value)


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"{path}: {exc}")


def write(path, text):
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        fail(f"{path}: {exc}")


def native(args):
    if len(args) != 4:
        fail(f"usage: {sys.argv[0]} --native ROOT CC CXX")
    _, root_arg, cc, cxx = args
    root = absolute_nonroot(root_arg)
    cc_path = absolute_nonroot(cc)
    cxx_path = absolute_nonroot(cxx)

    def cmake_quote(value):
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")

    compiler_file = root / "lib/cmake/Qt6/qt.toolchain.cmake"
    source_file = root / "lib/cmake/Qt6BuildInternals/QtBuildInternalsExtra.cmake"
    text = read(compiler_file)
    text, c_count = re.subn(
        r'^(set\(__qt_initial_c_compiler )"(?:\\.|[^"\\])*"\)',
        lambda match: f'{match.group(1)}"{cmake_quote(str(cc_path))}")',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text, cxx_count = re.subn(
        r'^(set\(__qt_initial_cxx_compiler )"(?:\\.|[^"\\])*"\)',
        lambda match: f'{match.group(1)}"{cmake_quote(str(cxx_path))}")',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if c_count != 1 or cxx_count != 1:
        fail(f"missing native compiler fields in {compiler_file}")
    write(compiler_file, text)

    text = read(source_file)
    text, count = re.subn(
        r'^(set\(QT_SOURCE_TREE )"[^"]*"',
        r'\1""',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        fail(f"missing source tree field in {source_file}")
    write(source_file, text)
    print("PASS: native Qt metadata uses selected compilers")


def target(args):
    module = args[-1:] == ["--module"]
    if module:
        args = args[:-1]
    if len(args) != 7:
        fail(f"usage: {sys.argv[0]} STAGED_QT SYSROOT WORKDIR PREFIX HOST_TOOLS_PREFIX TARGET_CC TARGET_CXX [--module]")
    root_arg, sysroot_arg, work_arg, prefix_arg, host_arg, target_cc_arg, target_cxx_arg = args
    root, sysroot, work, prefix, host_prefix, target_cc, target_cxx = map(
        absolute_nonroot,
        (root_arg, sysroot_arg, work_arg, prefix_arg, host_arg, target_cc_arg, target_cxx_arg),
    )

    if not (root / "lib/cmake").is_dir():
        fail("not a staged Qt module tree")
    if not module:
        if not (root / "lib/cmake/Qt6/Qt6Config.cmake").is_file():
            fail("not a staged Qtbase tree")
        if not (root / "bin/qmake").is_file():
            fail("target qmake missing")

    # These wrappers run the build machine's generators. Target qmake/qtpaths
    # are already built and installed separately by QT_FORCE_BUILD_TOOLS.
    for name in ("host-qmake", "host-qmake6", "host-qtpaths", "host-qtpaths6", "target_qt.conf"):
        path = root / "bin" / name
        if path.is_symlink() or path.exists():
            try:
                path.unlink()
            except OSError as exc:
                fail(f"{path}: {exc}")

    preliminary = root / "mkspecs/preliminary"
    if preliminary.is_symlink():
        preliminary.unlink()
    elif preliminary.is_dir():
        shutil.rmtree(preliminary)

    files = []
    for base in (root / "mkspecs", root / "lib", root / "sbom"):
        if not base.is_dir() or base.is_symlink():
            continue
        for current, dirs, names in os.walk(base, topdown=True, followlinks=False):
            current_path = Path(current)
            dirs[:] = [name for name in dirs if not (current_path / name).is_symlink()]
            for name in names:
                path = current_path / name
                if path.is_symlink() or not path.is_file():
                    continue
                if path.suffix in (".pri", ".prl", ".conf", ".pc", ".cmake"):
                    files.append(path)
                elif base == root / "sbom" and path.parent == base and path.suffix == ".spdx":
                    files.append(path)

    for name in ("bin/qt-cmake", "bin/qt-cmake-create", "libexec/qt-cmake-private"):
        path = root / name
        if path.is_file() and not path.is_symlink():
            files.append(path)

    for path in files:
        old = read(path)
        text = old
        spdx = path.parent == root / "sbom" and path.suffix == ".spdx"
        if spdx:
            pattern = re.compile(
                r"(^[a-z0-9][a-z0-9._+-]* was configured with:\n)(.*?)(?=^</text>$)",
                re.MULTILINE | re.DOTALL,
            )

            def normalize_configure(match):
                args = match.group(2)
                args = re.sub(
                    re.escape(str(work / ".buildlink")) + r'(?=/|["\s);])',
                    lambda _match: str(prefix),
                    args,
                )
                args = re.sub(
                    re.escape(str(host_prefix)) + r'(?=/|["\s);])',
                    "${SDK_NATIVE_PREFIX}",
                    args,
                )
                return match.group(1) + args

            text = pattern.sub(normalize_configure, text)
        else:
            text = re.sub(re.escape(str(sysroot)) + r"(?=/)", "", text)
            text = re.sub(
                re.escape(str(work / ".buildlink")) + r'(?=/|["\s)])',
                lambda _match: str(prefix),
                text,
            )

        # CMake does not sysroot absolute include directories on imported targets.
        # Qt's exported platform flags refer to the common prefix beside qt6.
        if path == root / "lib/cmake/Qt6/Qt6Targets.cmake":
            text = re.sub(
                r'(?<=[";])' + re.escape(str(prefix)) + r'/(include|lib)(?=[/";])',
                lambda match: "${_IMPORT_PREFIX}/../" + match.group(1),
                text,
            )

        text = re.sub(r"^PKG_CONFIG_EXECUTABLE\s*=.*$",
                      lambda _match: f"PKG_CONFIG_EXECUTABLE = {prefix}/bin/pkg-config",
                      text, flags=re.MULTILINE)
        text = re.sub(r"^QMAKE_CC\s*=.*$", lambda _match: f"QMAKE_CC = {target_cc}", text, flags=re.MULTILINE)
        text = re.sub(r"^QMAKE_CXX\s*=.*$", lambda _match: f"QMAKE_CXX = {target_cxx}", text, flags=re.MULTILINE)
        text = re.sub(r"^QMAKE_MKDIR\s*=.*$", "QMAKE_MKDIR = mkdir -p", text, flags=re.MULTILINE)
        text = re.sub(r'^original_cmake_path="[^"]*"$',
                      lambda _match: f'original_cmake_path="{prefix}/bin/cmake"',
                      text, flags=re.MULTILINE)
        text = re.sub(
            r'^(set\(__qt_platform_initial_qt_host_path(?:_cmake_dir)? )"[^"]*"\)',
            r'\1"")', text, flags=re.MULTILINE)
        text = re.sub(r'^(set\(QT_SOURCE_TREE )"[^"]*"', r'\1""', text, flags=re.MULTILINE)

        if path == root / "mkspecs/qmodule.pri":
            def disable_cross_compile(match):
                key, values = match.group(1), match.group(2)
                values = re.sub(r"\bcross_compile\b\s*", "", values)
                return key + values

            text = re.sub(
                r"^(CONFIG \+=|QT\.global_private\.enabled_features =)([^\n]*)",
                disable_cross_compile,
                text,
                flags=re.MULTILINE,
            )
            if not re.search(r"^QT\.global_private\.disabled_features =[^\n]*\bcross_compile\b", text, re.MULTILINE):
                text = re.sub(
                    r"^(QT\.global_private\.disabled_features =[^\n]*)$",
                    r"\1 cross_compile",
                    text,
                    count=1,
                    flags=re.MULTILINE,
                )

        if str(work) in text or (not spdx and str(sysroot) in text):
            fail(f"unresolved build path in {path}")
        if text != old:
            write(path, text)

    if not module:
        # qmake otherwise remembers the build host's mkspec. Relative paths keep the
        # installed SDK relocatable; this file also works after ordinary package install.
        write(root / "bin/qt.conf",
              "[Paths]\nPrefix=..\nHostPrefix=..\nHostData=.\nSysroot=\nSysrootifyPrefix=false\nTargetSpec=netbsd-g++\nHostSpec=netbsd-g++\n")
    print("PASS: target Qt metadata uses selected target compilers and paths")


if __name__ == "__main__":
    argv = sys.argv[1:]
    try:
        if argv and argv[0] == "--native":
            native(argv)
        else:
            target(argv)
    except (OSError, UnicodeError) as exc:
        fail(str(exc))
