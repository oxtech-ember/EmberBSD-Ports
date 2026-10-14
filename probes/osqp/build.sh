#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
umask 022
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo 'Usage: build.sh ABS_NEW_WORK [ABS_CACHE]' >&2; exit 2; }
work=$1
for directory in "$@"; do
    case "$directory" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2 ;; esac
    case "$directory" in *[!a-zA-Z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Work path already exists.' >&2; exit 2; }
case "$(uname -s):$(uname -p)" in NetBSD:aarch64) ;; *) echo 'Native NetBSD/aarch64 required.' >&2; exit 2 ;; esac
jobs=${JOBS:-1}
for value in "$jobs"; do
    case "$value" in ''|*[!0-9]*) echo 'Limits must be positive integers.' >&2; exit 2 ;; esac
    [ "$value" -gt 0 ] 2>/dev/null || exit 2
done
if [ "${BUILD_AS_KIB+x}" = x ]; then
    case "$BUILD_AS_KIB" in ''|*[!0-9]*) echo 'BUILD_AS_KIB must be positive.' >&2; exit 2 ;; esac
    [ "$BUILD_AS_KIB" -gt 0 ] 2>/dev/null || exit 2
    ulimit -S -v "$BUILD_AS_KIB"
fi
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
cmake=${CMAKE:-cmake}
for tool in "$cmake" ninja tar patch sha256; do command -v "$tool" >/dev/null; done
mkdir "$work"
mkdir "$work/src" "$work/archives" "$work/logs"
while read -r name expected url; do
    if [ "$#" = 2 ]; then cp "$2/$name" "$work/archives/$name";
    else curl -fLsS --connect-timeout 20 --max-time 900 "$url" -o "$work/archives/$name"; fi
    actual=$(sha256 -q "$work/archives/$name")
    [ "$actual" = "$expected" ] || { echo "Checksum mismatch: $name" >&2; exit 2; }
    printf '%s %s %s\n' "$name" "$actual" "$url" >> "$work/logs/sources.txt"
done < "$recipe/sources.tsv"
while read -r name expected; do
    [ "$(sha256 -q "$recipe/$name")" = "$expected" ] || { echo "Patch checksum mismatch: $name" >&2; exit 2; }
done < "$recipe/patches.tsv"
while read -r name expected url; do tar -mxf "$work/archives/$name" -C "$work/src"; done < "$recipe/sources.tsv"
while read -r name expected; do
    patch -d "$work/src/osqp-1.0.0" -p0 < "$recipe/$name" >> "$work/logs/patches.txt"
done < "$recipe/patches.tsv"
{ uname -a; "${CC:-cc}" --version; "$cmake" --version; ninja --version;
  printf 'JOBS=%s\nBUILD_AS_KIB=%s\n' "$jobs" "${BUILD_AS_KIB:-inherited}";
} > "$work/logs/tools.txt"
run()
{
    stage=$1; shift
    status=0
    "$@" > "$work/logs/$stage.log" 2>&1 || status=$?
    if [ "$status" -ne 0 ]; then tail -60 "$work/logs/$stage.log" >&2; exit "$status"; fi
}
prefix=$work/install
run configure "$cmake" -S "$work/src/osqp-1.0.0" -B "$work/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_INSTALL_RPATH="$prefix/lib" -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF \
    -DOSQP_VERSION=1.0.0 -DOSQP_ALGEBRA_BACKEND=builtin \
    -DOSQP_BUILD_SHARED_LIB=ON -DOSQP_BUILD_STATIC_LIB=OFF -DOSQP_BUILD_DEMO_EXE=OFF \
    -DOSQP_BUILD_UNITTESTS=OFF -DOSQP_USE_FLOAT=OFF -DOSQP_USE_LONG=ON \
    -DOSQP_ENABLE_INTERRUPT=ON -DOSQP_ENABLE_PROFILING=ON -DOSQP_ENABLE_PRINTING=ON \
    -DOSQP_ENABLE_DERIVATIVES=ON -DOSQP_CODEGEN=OFF -DOSQP_PROFILER_ANNOTATIONS=OFF \
    -DFETCHCONTENT_SOURCE_DIR_QDLDL="$work/src/qdldl-0.1.9" \
    -DFETCHCONTENT_FULLY_DISCONNECTED=ON -DFETCHCONTENT_UPDATES_DISCONNECTED=ON
run build "$cmake" --build "$work/build" --parallel "$jobs"
run install "$cmake" --install "$work/build"
mkdir -p "$prefix/share/ember-osqp/licenses"
cp "$recipe/sources.tsv" "$recipe/patches.tsv" "$recipe/PROVENANCE.md" "$prefix/share/ember-osqp/"
cp "$work/src/osqp-1.0.0/LICENSE" "$prefix/share/ember-osqp/licenses/OSQP-Apache-2.0"
cp "$work/src/osqp-1.0.0/NOTICE" "$prefix/share/ember-osqp/licenses/OSQP-NOTICE"
cp "$work/src/qdldl-0.1.9/LICENSE" "$prefix/share/ember-osqp/licenses/QDLDL-Apache-2.0"
cp "$work/src/osqp-1.0.0/algebra/_common/lin_sys/qdldl/amd/LICENSE" "$prefix/share/ember-osqp/licenses/AMD"
echo "Installed in $prefix; run test.sh next."
