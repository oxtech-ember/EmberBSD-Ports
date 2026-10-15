#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
umask 022
[ "$(uname -s)" = NetBSD ] || { echo 'Native EmberBSD/NetBSD required.' >&2; exit 2; }
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo 'Usage: build.sh NEW_WORK [ARCHIVE_DIRECTORY]' >&2; exit 2; }
work=$1
case "$work" in /*) ;; *) echo 'Use an absolute work path.' >&2; exit 2 ;; esac
case "$work" in *[!a-zA-Z0-9_./-]*) echo 'Use a simple path without whitespace.' >&2; exit 2 ;; esac
jobs=${JOBS:-1}
case "$jobs" in ''|0|*[!0-9]*) echo 'JOBS must be positive.' >&2; exit 2 ;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'JOBS must be positive.' >&2; exit 2; }
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
onnx_recipe=$recipe/../../pkgsrc/local-ai/onnxruntime
ncnn_recipe=$recipe/../../pkgsrc/local-ai/ncnn
patch_tool=${PATCH:-gpatch}
python=${PYTHON:-python3}
CC=${CC:-gcc}
CXX=${CXX:-g++}
export CC CXX
for tool in "$CC" "$CXX" cmake ninja gmake "$patch_tool" "$python" sha256 curl tar pkg-config; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }
done
for compiler in "$CC" "$CXX"; do
    [ "$("$compiler" -dumpfullversion)" = 16.2.0 ] || {
        echo 'The current profile requires GCC 16.2.0.' >&2; exit 2;
    }
done
mkdir "$work"
mkdir "$work/src" "$work/archives" "$work/logs" "$work/dependencies"
prefix=$work/install
if [ "$#" = 2 ]; then
    while read -r name hash url; do cp "$2/$name" "$work/archives/$name"; done < "$recipe/sources.tsv"
    while read -r name hash url; do cp "$2/$name" "$work/archives/$name"; done < "$recipe/dependencies.tsv"
fi
# Verify all archives before extracting any source. fetch.sh rejects corrupt caches.
sh "$recipe/fetch.sh" "$work/archives" > "$work/logs/sources.txt"
while read -r name hash url; do tar -xzf "$work/archives/$name" -C "$work/src"; done < "$recipe/sources.tsv"
while read -r name hash url; do
    mirror=$work/dependencies/${url#https://}
    mkdir -p "$(dirname "$mirror")"
    cp "$work/archives/$name" "$mirror"
done < "$recipe/dependencies.tsv"
while read -r file hash; do
    [ "$(sha256 -q "$work/src/silero-vad-6.2.3/$file")" = "$hash" ] || { echo "Model/fixture checksum mismatch: $file" >&2; exit 1; }
done < "$recipe/models.tsv"
run()
{
    stage=$1
    shift
    printf '%s\n' "$stage"
    status=0
    /usr/bin/time -l "$@" > "$work/logs/$stage.log" 2>&1 || status=$?
    if [ "$status" -ne 0 ]; then
        tail -60 "$work/logs/$stage.log" >&2
        echo "Failed: $stage ($status)" >&2
        exit "$status"
    fi
}
{ uname -a; "$CC" --version; "$CXX" --version; cmake --version; ninja --version; "$python" --version; } > "$work/logs/tools.txt"
run rnnoise-upstream-arm-build "$patch_tool" -d "$work/src/rnnoise-0.2" -p1 < "$recipe/patches/rnnoise-upstream-arm-build.patch"
cd "$work/src/rnnoise-0.2"
run rnnoise-configure ./configure --prefix="$prefix" --enable-shared --disable-static --disable-examples
run rnnoise-build gmake -j "$jobs"
run rnnoise-check gmake check
run rnnoise-install gmake install
for patch in "$ncnn_recipe"/patches/patch-*; do
    run "ncnn-$(basename "$patch")" "$patch_tool" -f -N -F 0 -d "$work/src/ncnn-20260526" -p1 < "$patch"
done
run ncnn-configure cmake -S "$work/src/ncnn-20260526" -B "$work/ncnn-build" -G Ninja \
    -C "$ncnn_recipe/features.cmake" -DCMAKE_INSTALL_PREFIX="$prefix"
run ncnn-build cmake --build "$work/ncnn-build" --parallel "$jobs"
run ncnn-install cmake --install "$work/ncnn-build"
run eigen-configure cmake -S "$work/src/eigen-5.0.1" -B "$work/eigen-build" -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$prefix" -DEIGEN_BUILD_TESTING=OFF -DEIGEN_BUILD_DOC=OFF \
    -DEIGEN_BUILD_BLAS=OFF -DEIGEN_BUILD_LAPACK=OFF -DEIGEN_BUILD_DEMOS=OFF
run eigen-install cmake --install "$work/eigen-build"
for patch in "$onnx_recipe"/patches/patch-*; do
    run "onnx-$(basename "$patch")" "$patch_tool" -f -N -F 0 -d "$work/src/onnxruntime-1.31.0" -p1 < "$patch"
done
run onnx-configure cmake -S "$work/src/onnxruntime-1.31.0/cmake" -B "$work/onnx-build" -G Ninja \
    -C "$onnx_recipe/features.cmake" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_PREFIX_PATH="$prefix" \
    -DCMAKE_CXX_STANDARD=20 \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DFETCHCONTENT_TRY_FIND_PACKAGE_MODE=NEVER \
    -Donnxruntime_CMAKE_DEPS_MIRROR_DIR="$work/dependencies" \
    -DPatch_EXECUTABLE="$(command -v "$patch_tool")" -DPython_EXECUTABLE="$(command -v "$python")" \
    -DFETCHCONTENT_FULLY_DISCONNECTED=OFF
run onnx-float16-contract sh "$recipe/tests/check-float16-source.sh" "$work"
run onnx-cpu-id-contract sh "$recipe/tests/check-netbsd-cpu-source.sh" "$work"
run onnx-build cmake --build "$work/onnx-build" --target onnxruntime onnxruntime_providers_shared --parallel "$jobs"
run onnx-install cmake -DCMAKE_INSTALL_LOCAL_ONLY=ON -P "$work/onnx-build/cmake_install.cmake"
run onnx-licenses sh "$onnx_recipe/files/install-licenses.sh" "$work/src/onnxruntime-1.31.0" "$work/onnx-build" "$prefix" "$onnx_recipe"
share=$prefix/share/ai-engines
mkdir -p "$share/models" "$share/fixtures" "$share/licenses"
cp "$work/src/silero-vad-6.2.3/src/silero_vad/data/silero_vad.onnx" "$share/models/"
cp "$work/src/silero-vad-6.2.3/tests/data/test.wav" "$share/fixtures/silero-test.wav"
cp "$recipe/sources.tsv" "$recipe/dependencies.tsv" "$recipe/models.tsv" "$recipe/PROVENANCE.md" "$share/"
cp "$recipe/LICENSE" "$share/licenses/EmberBSD-probe-LICENSE"
mkdir -p "$share/patches/onnxruntime" "$share/patches/ncnn"
cp "$recipe/patches/rnnoise-upstream-arm-build.patch" "$share/patches/"
cp "$onnx_recipe"/patches/patch-* "$share/patches/onnxruntime/"
cp "$ncnn_recipe"/patches/patch-* "$share/patches/ncnn/"
cp "$work/src/ncnn-20260526/LICENSE.txt" "$share/licenses/ncnn-LICENSE.txt"
cp "$work/src/rnnoise-0.2/COPYING" "$share/licenses/RNNoise-COPYING"
cp "$work/src/silero-vad-6.2.3/LICENSE" "$share/licenses/Silero-LICENSE"
mkdir -p "$share/licenses/eigen"
cp "$work/src/eigen-5.0.1"/COPYING* "$share/licenses/eigen/"
du -sk "$work" "$prefix" > "$work/logs/disk-kib.txt"
echo "Installed in $prefix; run test.sh to validate the installed consumers."
