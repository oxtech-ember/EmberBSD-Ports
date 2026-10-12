#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native upstream KWin protocol generator.
set -eu
[ "$#" = 4 ] || { echo 'Usage: build-kwin-scanner.sh DISTFILES HOST_QT ECM_CMAKE_DIR NEW_WORK' >&2; exit 2; }
dist=$1 qt=$2 ecm=$3 work=$4
: "${CMAKE:?}" "${NINJA:?}" "${HOST_CXX:?}"
for path in "$dist" "$qt" "$ecm" "$work" "$CMAKE" "$NINJA" "$HOST_CXX"; do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) exit 2;; esac
done
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
archive=kwin-6.7.5.tar.xz
expected=$(awk -F '\t' -v name="$archive" '$2 == name {print $3}' "$root/sources.tsv")
[ -n "$expected" ] && [ "$(shasum -a 256 "$dist/$archive" | awk '{print $1}')" = "$expected" ]
[ "$("$qt/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
mkdir "$work"
mkdir "$work/source" "$work/bin"
tar -xf "$dist/$archive" --strip-components=1 -C "$work/source"
"$CMAKE" -S "$work/source/src/wayland/tools" -B "$work/build" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_PREFIX_PATH="$qt" -DECM_DIR="$ecm" -DCMAKE_BUILD_TYPE=Release > "$work/configure.log" 2>&1
"$CMAKE" --build "$work/build" --parallel 2 > "$work/build.log" 2>&1
cp "$work/build/qtwaylandscanner_kde" "$work/bin/qtwaylandscanner_kde"
shasum -a 256 "$dist/$archive" "$work/bin/qtwaylandscanner_kde" "$0" > "$work/outputs.sha256"
echo 'Built native KWin protocol scanner; generated-code acceptance belongs to the cross consumer build'
