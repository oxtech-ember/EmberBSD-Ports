#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors. Prepared with AI assistance.
set -eu
probe=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
: "${PROTOBUF_WORK:?Set an absolute private build directory}"
: "${PKGSRC_BASE:?Set the pinned pkgsrc source root}"
jobs=${JOBS:-2}
case "$PROTOBUF_WORK" in /*) ;; *) echo "PROTOBUF_WORK must be absolute" >&2; exit 1;; esac
case "$jobs" in ''|*[!0-9]*|0) echo "JOBS must be positive" >&2; exit 1;; esac
mode=${1:-all}
case "$mode" in prepare|native|target|native-contracts|target-contracts|contracts|all) ;; *) echo "Unknown mode: $mode" >&2; exit 1;; esac
mkdir -p "$PROTOBUF_WORK/downloads" "$PROTOBUF_WORK/logs"
native=$PROTOBUF_WORK/native
export PROTOBUF_STAGE=${PROTOBUF_STAGE:-$PROTOBUF_WORK/stage}

check_compiler()
{
    version=$("$1" -dumpfullversion)
    [ "$version" = 16.2.0 ] || {
        echo "GCC 16.2.0 is required: $1 reports $version" >&2
        exit 1
    }
}

check_native()
{
    : "${NATIVE_CC:?Set the native GCC16 C compiler}"
    : "${NATIVE_CXX:?Set the native GCC16 C++ compiler}"
    check_compiler "$NATIVE_CC"
    check_compiler "$NATIVE_CXX"
    [ "$("$NATIVE_CC" -dumpmachine)" = "$("$NATIVE_CXX" -dumpmachine)" ] || {
        echo "Native C and C++ compiler targets differ" >&2
        exit 1
    }
}

check_target()
{
    : "${EMBERBSD_SYSROOT:?Set the coherent EmberBSD base sysroot}"
    : "${EMBERBSD_GCC_RUNTIME:?Set the common target GCC16 prefix}"
    : "${CROSS_PREFIX:?Set the GCC16 cross compiler command prefix}"
    check_compiler "${CROSS_PREFIX}gcc"
    check_compiler "${CROSS_PREFIX}g++"
    [ "$("${CROSS_PREFIX}gcc" -dumpmachine)" = aarch64--netbsd ] &&
        [ "$("${CROSS_PREFIX}g++" -dumpmachine)" = aarch64--netbsd ] || {
        echo "The target compiler must use the aarch64--netbsd triplet" >&2
        exit 1
    }
}

prepare_stage()
{
    work_real=$(realpath "$PROTOBUF_WORK")
    stage_real=$(realpath -m "$PROTOBUF_STAGE")
    case "$stage_real" in
        "$work_real"/*) ;;
        *) echo "PROTOBUF_STAGE must stay inside PROTOBUF_WORK" >&2; exit 1;;
    esac
    expected=$PROTOBUF_WORK/logs/stage-provenance.expected
    {
        echo 'EmberBSD protobuf 36.2, Abseil 20260817.0, GCC 16.2.0, aarch64--netbsd'
        realpath "$EMBERBSD_SYSROOT" "$EMBERBSD_GCC_RUNTIME"
        sha256sum "$EMBERBSD_SYSROOT/usr/lib/libc.so" "$EMBERBSD_GCC_RUNTIME/lib/libstdc++.so"
        cat "$PROTOBUF_WORK/abseil-cpp-20260817.0/.emberbsd-prepared"
        cat "$PROTOBUF_WORK/protobuf-36.2/.emberbsd-prepared"
    } > "$expected"
    if [ -e "$stage_real" ]; then
        [ -f "$stage_real/.emberbsd-protobuf-stage" ] || {
            echo "Existing stage has no ownership/provenance marker: $stage_real" >&2
            exit 1
        }
        cmp "$expected" "$stage_real/.emberbsd-protobuf-stage" || {
            echo "Stage inputs changed; use a new private work directory" >&2
            exit 1
        }
    else
        mkdir -p "$stage_real"
        cp "$expected" "$stage_real/.emberbsd-protobuf-stage"
    fi
}

prepare()
{
    for spec in \
        'protobuf-36.2.tar.gz|https://github.com/protocolbuffers/protobuf/releases/download/v36.2/protobuf-36.2.tar.gz' \
        'abseil-cpp-20260817.0.tar.gz|https://github.com/abseil/abseil-cpp/releases/download/20260817.0/abseil-cpp-20260817.0.tar.gz'; do
        name=${spec%%|*}
        url=${spec#*|}
        if [ ! -f "$PROTOBUF_WORK/downloads/$name" ]; then
            curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
                "$url" -o "$PROTOBUF_WORK/downloads/$name.part"
            mv "$PROTOBUF_WORK/downloads/$name.part" "$PROTOBUF_WORK/downloads/$name"
        fi
    done
    (cd "$PROTOBUF_WORK/downloads" && sha256sum -c "$probe/sources.sha256")
    for component in abseil protobuf; do
        case "$component" in
            abseil) name=abseil-cpp-20260817.0;;
            protobuf) name=protobuf-36.2;;
        esac
        wanted=$PROTOBUF_WORK/logs/$component-preparation.sha256
        (cd "$PROTOBUF_WORK/downloads" && sha256sum "$name.tar.gz") > "$wanted"
        (cd "$PKGSRC_BASE/devel/$component/patches" && sha256sum patch-*) >> "$wanted"
        if [ "$component" = protobuf ]; then
            for local_patch in "$probe/patches/"patch-*; do
                canonical_patch=$PKGSRC_BASE/devel/protobuf/patches/$(basename "$local_patch")
                if [ -f "$canonical_patch" ]; then
                    cmp "$local_patch" "$canonical_patch" || {
                        echo "The canonical protobuf patch differs: $canonical_patch" >&2
                        exit 1
                    }
                else
                    (cd "$probe/patches" && sha256sum "$(basename "$local_patch")") >> "$wanted"
                fi
            done
        fi
        if [ -e "$PROTOBUF_WORK/$name" ]; then
            [ -f "$PROTOBUF_WORK/$name/.emberbsd-prepared" ] || {
                echo "Existing source lacks the preparation stamp: $name" >&2
                exit 1
            }
            cmp "$wanted" "$PROTOBUF_WORK/$name/.emberbsd-prepared" || {
                echo "The source inputs changed; use a new private work directory" >&2
                exit 1
            }
            continue
        fi
        tar -xf "$PROTOBUF_WORK/downloads/$name.tar.gz" -C "$PROTOBUF_WORK"
        for patchfile in "$PKGSRC_BASE/devel/$component/patches/"patch-*; do
            [ -f "$patchfile" ] || { echo "Missing $component patch set" >&2; exit 1; }
            patch --fuzz=0 -d "$PROTOBUF_WORK/$name" -p0 < "$patchfile"
            sha256sum "$patchfile" >> "$PROTOBUF_WORK/logs/source-patches.sha256"
        done
        if [ "$component" = protobuf ]; then
            for local_patch in "$probe/patches/"patch-*; do
                canonical_patch=$PKGSRC_BASE/devel/protobuf/patches/$(basename "$local_patch")
                if [ ! -f "$canonical_patch" ]; then
                    patch --fuzz=0 -d "$PROTOBUF_WORK/$name" -p0 < "$local_patch"
                    sha256sum "$local_patch" >> "$PROTOBUF_WORK/logs/source-patches.sha256"
                fi
            done
        fi
        cp "$wanted" "$PROTOBUF_WORK/$name/.emberbsd-prepared"
    done
}

check_native_zlib()
{
    : "${NATIVE_ZLIB_PREFIX:?Set the common native zlib 1.3.2 prefix}"
    case "$NATIVE_ZLIB_PREFIX" in
        /*) ;;
        *) echo "NATIVE_ZLIB_PREFIX must be absolute" >&2; exit 1;;
    esac
    [ -f "$NATIVE_ZLIB_PREFIX/include/zlib.h" ] &&
        [ -f "$NATIVE_ZLIB_PREFIX/lib/libz.so" ] &&
        grep -Eq '^#define[[:space:]]+ZLIB_VERSION[[:space:]]+"1\.3\.2"' \
            "$NATIVE_ZLIB_PREFIX/include/zlib.h" || {
        echo "The native provider must contain shared zlib 1.3.2" >&2
        exit 1
    }
}

native_build()
{
    check_native
    check_native_zlib
    cmake -S "$PROTOBUF_WORK/abseil-cpp-20260817.0" -B "$PROTOBUF_WORK/build-native-abseil" \
        -G Ninja -DCMAKE_C_COMPILER="$NATIVE_CC" -DCMAKE_CXX_COMPILER="$NATIVE_CXX" \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 -DBUILD_SHARED_LIBS=ON \
        -DCMAKE_INSTALL_PREFIX="$native" -DCMAKE_INSTALL_RPATH="$native/lib" \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    cmake --build "$PROTOBUF_WORK/build-native-abseil" -j "$jobs"
    cmake --install "$PROTOBUF_WORK/build-native-abseil"
    cmake -S "$PROTOBUF_WORK/protobuf-36.2" -B "$PROTOBUF_WORK/build-native-protobuf" \
        -G Ninja -DCMAKE_C_COMPILER="$NATIVE_CC" -DCMAKE_CXX_COMPILER="$NATIVE_CXX" \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 \
        -Dprotobuf_BUILD_SHARED_LIBS=ON -Dprotobuf_LOCAL_DEPENDENCIES_ONLY=ON \
        -DZLIB_INCLUDE_DIR="$NATIVE_ZLIB_PREFIX/include" \
        -DZLIB_LIBRARY_RELEASE="$NATIVE_ZLIB_PREFIX/lib/libz.so" \
        -DCMAKE_PREFIX_PATH="$native" -DCMAKE_INSTALL_PREFIX="$native" \
        -DCMAKE_INSTALL_RPATH="$native/lib;$NATIVE_ZLIB_PREFIX/lib" \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    cmake --build "$PROTOBUF_WORK/build-native-protobuf" -j "$jobs"
    cmake --install "$PROTOBUF_WORK/build-native-protobuf"
    "$native/bin/protoc" --version
}

target_build()
(
    unset LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH OBJC_INCLUDE_PATH
    check_target
    prepare_stage
    for component in abseil protobuf; do
        case "$component" in
            abseil) name=abseil-cpp-20260817.0; set -- -DBUILD_SHARED_LIBS=ON;;
            protobuf) name=protobuf-36.2; set -- -Dprotobuf_BUILD_SHARED_LIBS=ON \
                -Dprotobuf_LOCAL_DEPENDENCIES_ONLY=ON;;
        esac
        cmake -S "$PROTOBUF_WORK/$name" -B "$PROTOBUF_WORK/build-target-$component" \
            -G Ninja -DCMAKE_TOOLCHAIN_FILE="$probe/aarch64.cmake" \
            -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 \
            -DCMAKE_INSTALL_PREFIX=/usr/pkg -DCMAKE_PREFIX_PATH=/usr/pkg \
            -DCMAKE_EXPORT_COMPILE_COMMANDS=ON "$@"
        cmake --build "$PROTOBUF_WORK/build-target-$component" -j "$jobs"
        DESTDIR="$PROTOBUF_STAGE" cmake --install "$PROTOBUF_WORK/build-target-$component"
    done
)

native_contracts()
{
    check_native
    check_native_zlib
    cmake -S "$probe" -B "$PROTOBUF_WORK/build-native-contract" -G Ninja \
        -DCMAKE_C_COMPILER="$NATIVE_CC" -DCMAKE_CXX_COMPILER="$NATIVE_CXX" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_PREFIX_PATH="$native" \
        -DZLIB_INCLUDE_DIR="$NATIVE_ZLIB_PREFIX/include" \
        -DZLIB_LIBRARY_RELEASE="$NATIVE_ZLIB_PREFIX/lib/libz.so" \
        -DNATIVE_PROTOC="$native/bin/protoc" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    cmake --build "$PROTOBUF_WORK/build-native-contract" -j "$jobs"
    "$PROTOBUF_WORK/build-native-contract/emberbsd-protobuf-contract"
    "$PROTOBUF_WORK/build-native-contract/emberbsd-upb-oom-contract"
}

target_contracts()
(
    unset LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH OBJC_INCLUDE_PATH
    check_target
    prepare_stage
    cmake -S "$probe" -B "$PROTOBUF_WORK/build-target-contract" -G Ninja \
        -DCMAKE_TOOLCHAIN_FILE="$probe/aarch64.cmake" -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCMAKE_INSTALL_PREFIX=/usr/pkg -DCMAKE_PREFIX_PATH=/usr/pkg \
        -DNATIVE_PROTOC="$native/bin/protoc" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    cmake --build "$PROTOBUF_WORK/build-target-contract" -j "$jobs"
    DESTDIR="$PROTOBUF_STAGE" cmake --install "$PROTOBUF_WORK/build-target-contract"
)

case "$mode" in prepare|all) prepare;; esac
case "$mode" in native|all) native_build;; esac
case "$mode" in target|all) target_build;; esac
case "$mode" in native-contracts|contracts|all) native_contracts;; esac
case "$mode" in target-contracts|contracts|all) target_contracts;; esac
