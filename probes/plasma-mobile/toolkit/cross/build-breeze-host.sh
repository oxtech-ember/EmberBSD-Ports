#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), build only Breeze's native resource generators.
set -eu
[ "$#" = 5 ] || { echo 'Usage: build-breeze-host.sh DISTFILES HOST_QT NATIVE_PREFIX ECM_CMAKE_DIR NEW_WORK' >&2; exit 2; }
distfiles=$1 qt=$2 native=$3 ecm=$4 work=$5
: "${CMAKE:?Set native CMake}" "${NINJA:?Set native Ninja}" "${HOST_CC:?Set native C compiler}" "${HOST_CXX:?Set native C++ compiler}" "${HOST_PYTHON:?Set native Python}"
: "${JOBS:=2}"
for item in "$distfiles" "$qt" "$native" "$ecm" "$work" "$CMAKE" "$NINJA" "$HOST_CC" "$HOST_CXX" "$HOST_PYTHON"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$item" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell/CMake metacharacters' >&2; exit 2;; esac
done
[ "$("$qt/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
archive=breeze-icons-6.31.0.tar.xz
expected=$(awk -F '\t' -v name="$archive" '$2 == name { print $3 }' "$root/sources.tsv")
[ -n "$expected" ] && [ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = "$expected" ]
mkdir "$work"
mkdir "$work/source" "$work/prefix" "$work/prefix/bin" "$work/prefix/share"
tar -xf "$distfiles/$archive" -C "$work/source"
recipe=$root/../../../pkgsrc/graphics/breeze-icons
for patch_name in $(awk '/^SHA1 \(patch-/ { gsub(/[()]/,"",$2); print $2 }' "$recipe/distinfo"); do
    expected=$(awk -v name="($patch_name)" '$1 == "SHA1" && $2 == name { print $4 }' "$recipe/distinfo")
    [ "$(shasum -a 1 "$recipe/patches/$patch_name" | awk '{print $1}')" = "$expected" ]
    patch -f -N -F 0 -p0 -d "$work/source/breeze-icons-6.31.0" -i "$recipe/patches/$patch_name" >> "$work/patch.log"
done

"$CMAKE" -S "$work/source/breeze-icons-6.31.0" -B "$work/build" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_C_COMPILER="$HOST_CC" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_PREFIX_PATH="$qt;$native" -DECM_DIR="$ecm" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_INSTALL_PREFIX="$work/prefix" \
    -DPython_EXECUTABLE="$HOST_PYTHON" -DBUILD_TESTING=OFF -DWITH_ICONS_LIBRARY=OFF \
    > "$work/configure.log" 2>&1
"$CMAKE" --build "$work/build" --parallel "$JOBS" --target generate-symbolic-dark qrcAlias > "$work/build.log" 2>&1
for program in generate-symbolic-dark qrcAlias; do
    cp "$work/build/bin/$program" "$work/prefix/bin/$program"
    [ -x "$work/prefix/bin/$program" ]
    shasum -a 256 "$work/prefix/bin/$program" >> "$work/outputs.sha256"
done
printf '6.31.0\n' > "$work/prefix/share/ember-breeze-version"
printf 'Built native Breeze generators: %s/prefix/bin\n' "$work"
