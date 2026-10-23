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
version=$(awk '$1 == "PLASMAVER?=" { if (NF != 2) exit 2; value=$2; count++ }
    END { if (count != 1) exit 2; print value }' "$root/../../../pkgsrc/meta-pkgs/kde/plasma6.mk")
printf '%s\n' "$version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'
selection=$(awk -F '\t' '$1 == "x11/plasma6-kwin" { archive=$2; hash=$3; count++ }
    END { if (count != 1) exit 2; print archive " " hash }' "$root/sources.tsv") || {
    echo 'Exactly one canonical KWin source is required' >&2; exit 2;
}
archive=${selection%% *} expected=${selection#* }
[ "$archive" = "kwin-$version.tar.xz" ] || {
    echo 'KWin manifest differs from the shared Plasma version' >&2; exit 2;
}
printf '%s\n' "$expected" | grep -Eq '^[0-9a-f]{64}$'
[ "$(shasum -a 256 "$dist/$archive" | awk '{print $1}')" = "$expected" ] || {
    echo 'KWin source archive checksum mismatch' >&2; exit 2;
}
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
