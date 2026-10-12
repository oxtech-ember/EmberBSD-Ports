#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native upstream Sonnet resource generator.
set -eu
[ "$#" = 4 ] || { echo 'Usage: build-sonnet-tool.sh DISTFILES HOST_QT ECM_CMAKE_DIR NEW_WORK' >&2; exit 2; }
distfiles=$1 qt=$2 ecm=$3 work=$4
: "${CMAKE:?Set native CMake}"
: "${NINJA:?Set native Ninja}"
: "${HOST_CC:?Set native C compiler}"
: "${HOST_CXX:?Set native C++ compiler}"
for path in "$distfiles" "$qt" "$ecm" "$work" "$CMAKE" "$NINJA" "$HOST_CC" "$HOST_CXX"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell/CMake metacharacters' >&2; exit 2;; esac
done
[ "$("$qt/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
toolkit=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
archive=sonnet-6.31.0.tar.xz
expected=$(awk -F '\t' '$1 == "textproc/kf6-sonnet" { print $3 }' "$toolkit/sources.tsv")
[ -n "$expected" ] && [ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = "$expected" ]
mkdir "$work"
mkdir "$work/source" "$work/bin"
tar -xf "$distfiles/$archive" -C "$work/source"
# Native build produces only the generator. The target package retains all backends/UI.
"$CMAKE" -S "$work/source/sonnet-6.31.0" -B "$work/build" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_C_COMPILER="$HOST_CC" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_PREFIX_PATH="$qt" -DECM_DIR="$ecm" -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTING=OFF -DSONNET_USE_WIDGETS=OFF -DSONNET_USE_QML=OFF -DSONNET_NO_BACKENDS=ON \
    -DQt6LinguistTools_DIR="$qt/lib/cmake/Qt6LinguistTools" > "$work/configure.log" 2>&1
"$CMAKE" --build "$work/build" --target parsetrigrams --parallel "${JOBS:-2}" > "$work/build.log" 2>&1
cp "$work/build/bin/parsetrigrams6" "$work/bin/parsetrigrams6"
"$work/bin/parsetrigrams6" "$work/source/sonnet-6.31.0/data/trigrams" > "$work/trigrams.map"
[ -s "$work/trigrams.map" ]
result=0
"$work/bin/parsetrigrams6" > "$work/missing-argument.log" 2>&1 || result=$?
[ "$result" = 1 ]
shasum -a 256 "$0" "$distfiles/$archive" "$work/bin/parsetrigrams6" "$work/trigrams.map" > "$work/inputs-output.sha256"
file "$work/bin/parsetrigrams6" > "$work/architecture.txt"
echo 'PASS: native Sonnet generator builds and creates the full language model'
