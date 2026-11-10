#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 4 ] || { echo 'Usage: install-licenses.sh SOURCE BUILD PREFIX RECIPE' >&2; exit 2; }
source=$1 build=$2 prefix=$3 recipe=$4
licenses=$prefix/share/licenses/onnxruntime
# Fail if an expected source or its notice is absent. A completed build
# must preserve the exact internal source set, including header-only inputs.
for name in abseil_cpp date flatbuffers gsl mp11 nlohmann_json onnx protobuf re2 safeint; do
    dependency=$build/_deps/$name-src
    [ -d "$dependency" ] || { echo "Missing dependency source: $name" >&2; exit 1; }
    if [ "$name" = mp11 ]; then
        # The standalone upstream mp11 archive omits LICENSE_1_0.txt.
        # Its header supplies the original copyright and license reference.
        [ -f "$dependency/include/boost/mp11.hpp" ] || exit 1
        continue
    fi
    found=no
    for notice in "$dependency"/LICENSE* "$dependency"/COPYING* "$dependency"/NOTICE*; do
        [ ! -f "$notice" ] || found=yes
    done
    [ "$found" = yes ] || { echo "Missing dependency notice: $name" >&2; exit 1; }
done
mkdir -p "$licenses" "$prefix/share/doc/onnxruntime"
cp "$source/LICENSE" "$licenses/LICENSE"
cp "$source/ThirdPartyNotices.txt" "$licenses/ThirdPartyNotices.txt"
cp "$recipe/files/SOURCE" "$prefix/share/doc/onnxruntime/SOURCE"
mkdir -p "$licenses/eigen5"
cp "$recipe/licenses/eigen5/"* "$licenses/eigen5/"
mkdir -p "$licenses/mp11"
cp "$recipe/licenses/BSL-1.0.txt" "$licenses/mp11/LICENSE_1_0.txt"
cp "$build/_deps/mp11-src/include/boost/mp11.hpp" "$licenses/mp11/copyright-notice.hpp"
for dependency in "$build"/_deps/*-src; do
    [ -d "$dependency" ] || continue
    name=$(basename "$dependency" -src)
    mkdir -p "$licenses/$name"
    for notice in "$dependency"/LICENSE* "$dependency"/COPYING* "$dependency"/NOTICE*; do
        [ -f "$notice" ] || continue
        cp "$notice" "$licenses/$name/"
    done
done
