#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 1 ] || { echo 'Usage: test.sh WORK' >&2; exit 2; }
work=$1
case "$work" in /*) ;; *) echo 'Use an absolute work path.' >&2; exit 2 ;; esac
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
CC=${CC:-gcc}
CXX=${CXX:-g++}
export CC CXX
for compiler in "$CC" "$CXX"; do
    [ "$("$compiler" -dumpfullversion)" = 16.2.0 ] || {
        echo 'The current profile requires GCC 16.2.0.' >&2; exit 2;
    }
done
prefix=$work/install
export PKG_CONFIG_PATH="$prefix/lib/pkgconfig:$prefix/share/pkgconfig"
export LD_LIBRARY_PATH="$prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export ORT_DISABLE_TELEMETRY=1
cmake -S "$recipe/tests" -B "$work/test-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$prefix" -DAI_DATA="$prefix/share/ai-engines"
cmake --build "$work/test-build" --parallel 1
ctest --test-dir "$work/test-build" --output-on-failure
for program in onnx-contract ncnn-contract rnnoise-contract silero-contract; do
    ldd "$work/test-build/$program"
done > "$work/logs/installed-linkage.txt"
if grep -q 'not found' "$work/logs/installed-linkage.txt"; then
    echo 'Missing runtime library.' >&2; exit 1
fi
for library in libonnxruntime.so libncnn.so librnnoise.so; do
    grep -F "$prefix/lib/$library" "$work/logs/installed-linkage.txt" >/dev/null || { echo "Wrong installed linkage: $library" >&2; exit 1; }
done
