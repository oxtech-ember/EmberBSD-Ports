#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native upstream KDSoap WSDL generator.
set -eu
[ "$#" = 4 ] || { echo 'Usage: build-kdsoap-wsdl-host.sh DISTFILES HOST_QT NEW_WORK KDSOAP_ARCHIVE' >&2; exit 2; }
dist=$1 qt=$2 work=$3 archive=$4
: "${CMAKE:?}" "${NINJA:?}" "${HOST_CXX:?}"
for path in "$dist" "$qt" "$work" "$CMAKE" "$NINJA" "$HOST_CXX"; do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) exit 2;; esac
done
[ "$("$qt/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
mkdir "$work"
mkdir "$work/source" "$work/bin"
tar -xf "$dist/$archive" --strip-components=1 -C "$work/source"
"$CMAKE" -S "$work/source" -B "$work/build" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_PREFIX_PATH="$qt" -DCMAKE_BUILD_TYPE=Release \
    -DKDSoap_QT6=ON -DKDSoap_EXAMPLES=OFF -DBUILD_TESTING=OFF \
    > "$work/configure.log" 2>&1
"$CMAKE" --build "$work/build" --target kdwsdl2cpp --parallel 2 > "$work/build.log" 2>&1
cp "$work/build/bin/kdwsdl2cpp-qt6" "$work/bin/kdwsdl2cpp-qt6"
file "$work/bin/kdwsdl2cpp-qt6" | grep -q 'Mach-O'
# kdwsdl2cpp has no --version; the consumer build exercises the tool on real WSDL files.
shasum -a 256 "$dist/$archive" "$work/bin/kdwsdl2cpp-qt6" "$0" > "$work/outputs.sha256"
echo 'Built native KDSoap WSDL generator; generated-code acceptance belongs to the cross consumer build'
