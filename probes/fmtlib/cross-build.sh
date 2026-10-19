#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted GCC16 target package probe.
set -eu
umask 022
[ "$#" = 4 ] || { echo 'Usage: cross-build.sh GCC_PREFIX SYSROOT FMT_ARCHIVE NEW_OUTPUT' >&2; exit 2; }
prefix=$1 sysroot=$2 archive=$3 out=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ -n "${TMPDIR:-}" ] || { echo 'Set TMPDIR to a task-specific path on the build volume.' >&2; exit 2; }
case "$TMPDIR" in /*) ;; *) echo 'TMPDIR must be absolute.' >&2; exit 2;; esac
case "$TMPDIR" in *[!A-Za-z0-9_./-]*) echo 'Use a simple TMPDIR path.' >&2; exit 2;; esac
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
recipe=$ports/profiles/common-graphics/recipes/textproc/fmtlib
manifest=$ports/profiles/common-graphics/sources.tsv
expected_archive=$(awk -F '\t' '$1 == "textproc/fmtlib" {print $2}' "$manifest")
expected_sha=$(awk -F '\t' '$1 == "textproc/fmtlib" {print $3}' "$manifest")
[ "$(basename -- "$archive")" = "$expected_archive" ] || { echo 'Unexpected fmt archive name.' >&2; exit 2; }
python3 - "$archive" "$recipe/distinfo" "$expected_sha" <<'PY'
import hashlib
import re
import sys
from pathlib import Path

archive = Path(sys.argv[1])
distinfo = Path(sys.argv[2]).read_text(encoding="utf-8")
expected_sha256 = sys.argv[3]
data = archive.read_bytes()
checks = {
    "BLAKE2s": hashlib.blake2s(data).hexdigest(),
    "SHA512": hashlib.sha512(data).hexdigest(),
}
for algorithm, actual in checks.items():
    match = re.search(rf"^{algorithm} \({re.escape(archive.name)}\) = ([0-9a-f]+)$", distinfo, re.M)
    if not match or match.group(1) != actual:
        raise SystemExit(f"{algorithm} mismatch for {archive.name}")
if hashlib.sha256(data).hexdigest() != expected_sha256:
    raise SystemExit("sources.tsv SHA256 mismatch")
match = re.search(rf"^Size \({re.escape(archive.name)}\) = ([0-9]+) bytes?$", distinfo, re.M)
if not match or int(match.group(1)) != len(data):
    raise SystemExit("archive size mismatch")
PY
for compiler in gcc g++; do
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpfullversion)" = 16.2.0 ]
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpmachine)" = aarch64--netbsd ]
done
mkdir -p "$out/source" "$out/build" "$out/stage" "$out/consumer" "$out/logs" "$TMPDIR"
df -Pk "$out" > "$out/logs/space-before.txt"
printf 'output=%s\nTMPDIR=%s\nsysroot=%s\n' "$out" "$TMPDIR" "$sysroot" > "$out/logs/paths.txt"
cp "$manifest" "$out/sources.tsv"
shasum -a 256 "$archive" "$manifest" "$recipe/Makefile" "$recipe/DESCR" \
    "$recipe/PLIST" "$recipe/distinfo" "$recipe/buildlink3.mk" "$0" \
    "$ports/probes/fmtlib/tests/CMakeLists.txt" \
    "$ports/probes/fmtlib/tests/formatting.cc" > "$out/inputs.sha256"
tar -xf "$archive" --strip-components=1 -C "$out/source"
if [ -d "$recipe/patches" ]; then
    for patch_file in "$recipe/patches"/patch-*; do
        [ -f "$patch_file" ] || continue
        name=${patch_file##*/}
        expected=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name {print $4}' "$recipe/distinfo")
        actual=$(sed '/[$]NetBSD.*/d' "$patch_file" | shasum -a 1 | awk '{print $1}')
        [ -n "$expected" ] && [ "$expected" = "$actual" ] || { echo "Patch checksum mismatch: $name" >&2; exit 1; }
        patch -f -F 0 -p0 -d "$out/source" < "$patch_file" > "$out/logs/$name.log" 2>&1
    done
fi
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
headers=$sysroot/usr/pkg/gcc16/include/c++
cat > "$out/toolchain.cmake" <<EOF
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_C_COMPILER $prefix/bin/aarch64--netbsd-gcc)
set(CMAKE_CXX_COMPILER $prefix/bin/aarch64--netbsd-g++)
set(CMAKE_C_FLAGS_INIT "-B$crt/ -L$runtime")
set(CMAKE_CXX_FLAGS_INIT "-B$crt/ -L$runtime -isystem $headers -isystem $headers/aarch64--netbsd -isystem $headers/backward")
set(CMAKE_EXE_LINKER_FLAGS_INIT "-L$runtime -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-rpath-link,$sysroot/usr/pkg/lib -Wl,-rpath-link,$runtime")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "-L$runtime -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-rpath-link,$sysroot/usr/pkg/lib -Wl,-rpath-link,$runtime")
set(CMAKE_MODULE_LINKER_FLAGS_INIT "-L$runtime -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-rpath-link,$sysroot/usr/pkg/lib -Wl,-rpath-link,$runtime")
set(CMAKE_FIND_ROOT_PATH $sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
EOF
cmake -S "$out/source" -B "$out/build" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/pkg \
    -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_INCLUDEDIR=include \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DBUILD_SHARED_LIBS=ON -DFMT_DOC=OFF -DFMT_INSTALL=ON -DFMT_TEST=OFF \
    > "$out/logs/configure.log" 2>&1
cmake --build "$out/build" --parallel "${CROSS_JOBS:-4}" > "$out/logs/build.log" 2>&1
DESTDIR="$out/stage" cmake --install "$out/build" > "$out/logs/install.log" 2>&1
cmake -S "$ports/probes/fmtlib/tests" -B "$out/consumer" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" \
    -Dfmt_DIR="$out/stage/usr/pkg/lib/cmake/fmt" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' \
    > "$out/logs/consumer-configure.log" 2>&1
cmake --build "$out/consumer" --parallel 2 > "$out/logs/consumer-build.log" 2>&1
readelf=$prefix/bin/aarch64--netbsd-readelf
"$readelf" -h "$out/consumer/fmtlib-contract" > "$out/logs/consumer-elf-header.txt"
"$readelf" -d "$out/stage/usr/pkg/lib/libfmt.so.12.2.0" > "$out/logs/library-dynamic.txt"
"$readelf" -d "$out/consumer/fmtlib-contract" > "$out/logs/consumer-dynamic.txt"
file "$out/consumer/fmtlib-contract" > "$out/logs/consumer-file.txt"
grep -q 'for NetBSD' "$out/logs/consumer-file.txt"
grep -E 'Library (rpath|runpath): \[/usr/pkg/gcc16/lib\]' "$out/logs/library-dynamic.txt" >/dev/null
grep -E 'Library (rpath|runpath): ' "$out/logs/consumer-dynamic.txt" | grep -F '/usr/pkg/lib' | grep -F '/usr/pkg/gcc16/lib' >/dev/null
if grep -hE 'RPATH|RUNPATH|NEEDED' "$out/logs/library-dynamic.txt" "$out/logs/consumer-dynamic.txt" | grep -F "$out"; then
    echo 'Build-host path leaked into target linkage.' >&2
    exit 1
fi
(cd "$out/stage/usr/pkg" && find . \( -type f -o -type l \) -print | sed 's|^./||' | LC_ALL=C sort) > "$out/logs/files.txt"
sed '/^@comment/d' "$recipe/PLIST" | LC_ALL=C sort > "$out/logs/plist.txt"
cmp "$out/logs/files.txt" "$out/logs/plist.txt"
shasum -a 256 "$out/stage/usr/pkg/lib/libfmt.so.12.2.0" \
    "$out/consumer/fmtlib-contract" > "$out/outputs.sha256"
df -Pk "$out" > "$out/logs/space-after.txt"
echo "PASS: fmt 12.2.0 GCC16 AArch64 stage and CMake consumer: $out/stage/usr/pkg"
