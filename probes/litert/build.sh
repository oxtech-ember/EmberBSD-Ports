#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
umask 022
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || {
    echo 'Usage: build.sh WORK_DIRECTORY [ARCHIVE_DIRECTORY]' >&2; exit 2;
}
: "${EMBER_CROSS_PREFIX:?Set the NetBSD/AArch64 GCC16 executable prefix}"
: "${EMBER_SYSROOT:?Set the matching target sysroot}"
ml_dtypes=${EMBER_ML_DTYPES_SOURCE:-$EMBER_SYSROOT/usr/pkg/share/ml-dtypes-source}
[ -f "$ml_dtypes/ml_dtypes/include/float8.h" ] || {
    echo 'Install devel/ml-dtypes in the sysroot or set EMBER_ML_DTYPES_SOURCE to its prepared tree.' >&2
    exit 2
}
ml_dtypes=$(CDPATH= cd "$ml_dtypes" && pwd)
work=$1
case "$work" in /*) ;; *) echo 'Use an absolute work directory.' >&2; exit 2 ;; esac
case "$work$EMBER_CROSS_PREFIX$EMBER_SYSROOT" in *[!a-zA-Z0-9_./-]*)
    echo 'Use paths without whitespace or shell metacharacters.' >&2; exit 2 ;; esac
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
jobs=${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu)}
case "$jobs" in ''|0|*[!0-9]*) echo 'JOBS must be positive.' >&2; exit 2 ;; esac
for tool in cmake ninja curl tar patch; do
    command -v "$tool" >/dev/null || { echo "Missing host tool: $tool" >&2; exit 2; }
done
command -v sha256 >/dev/null 2>&1 || command -v shasum >/dev/null 2>&1 || {
    echo 'Missing SHA256 tool.' >&2; exit 2;
}
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
mkdir -p "$work/cache" "$work/deps" "$work/src" "$work/logs"
if [ "$#" = 2 ]; then
    for manifest in "$recipe/sources.tsv" "$recipe/dependencies.tsv"; do
        while read -r name hash url; do
            [ -f "$work/cache/$name.tar.gz" ] || cp "$2/$name.tar.gz" "$work/cache/"
        done < "$manifest"
    done
fi
sh "$recipe/fetch.sh" "$work/cache" > "$work/logs/sources.txt"
if [ ! -f "$work/.sources-prepared" ]; then
    for manifest in sources dependencies; do
        while read -r name hash url; do
            case "$name" in
                litert-v2.2.0) destination=$work/src/LiteRT-2.2.0 ;;
                litert-lm-v0.18.0) destination=$work/src/LiteRT-LM-0.18.0 ;;
                *) destination=$work/deps/$name ;;
            esac
            [ ! -e "$destination" ] || {
                echo "Unmarked source directory exists: $destination; choose a clean work directory." >&2; exit 2;
            }
            mkdir "$destination"
            tar -xzf "$work/cache/$name.tar.gz" --strip-components=1 -C "$destination"
        done < "$recipe/$manifest.tsv"
    done
    for patch_file in "$recipe"/patches/litert-*.patch; do
        patch -d "$work/src/LiteRT-2.2.0" -p1 < "$patch_file"
    done
    patch -d "$work/deps/xnnpack" -p1 < "$recipe/patches/xnnpack-netbsd.patch"
    patch -d "$work/deps/ruy" -p1 < "$recipe/patches/ruy-netbsd.patch"
    touch "$work/.sources-prepared"
fi
run()
{
    stage=$1; shift
    printf '%s\n' "$stage"
    if "$@" > "$work/logs/$stage.log" 2>&1; then return; fi
    tail -60 "$work/logs/$stage.log" >&2
    exit 1
}
run host-configure cmake -S "$recipe/host" -B "$work/host-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DEMBER_DEPS="$work/deps"
run host-build cmake --build "$work/host-build" --target flatc protoc --parallel "$jobs"
run regenerate sh "$recipe/regenerate-schemas.sh" "$work/host-build/flatbuffers/flatc" \
    "$work/src/LiteRT-2.2.0" "$work/deps/tensorflow"
run target-configure cmake -S "$recipe" -B "$work/target-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/pkg \
    -DCMAKE_TOOLCHAIN_FILE="$recipe/cmake/netbsd-aarch64.cmake" \
    -DEMBER_DEPS="$work/deps" -DEMBER_HOST_TOOLS="$work/host-build" -DEMBER_ML_DTYPES_SOURCE="$ml_dtypes" \
    -DEMBER_LITERT_SOURCE_DIR="$work/src/LiteRT-2.2.0" \
    -DEMBER_LITERT_LM_SOURCE_DIR="$work/src/LiteRT-LM-0.18.0" \
    -DEMBER_MINIZIP_SOURCE_DIR="$work/deps/zlib/contrib/minizip"
run target-build cmake --build "$work/target-build" --target ember_litert_bundle --parallel "$jobs"
run target-install env DESTDIR="$work/stage" cmake --install "$work/target-build" --component EmberLiteRt
printf 'Target files: %s/stage/usr/pkg\n' "$work"
