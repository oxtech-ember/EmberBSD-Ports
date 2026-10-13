#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Test exported include paths without compiling.
set -eu
[ "$#" = 3 ] || {
    echo "Usage: $0 SOURCE_ARCHIVE INSTALLED_PREFIX NEW_OUTPUT" >&2
    exit 2
}
: "${CMAKE:?Set native CMake}"
archive=$1 installed=$2 out=$3
for item in "$@" "$CMAKE"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
recipe=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = d287119db9dc3113bb3a2b0e78ce8670e064b744c14d3aaec69799374aadb00b ]
mkdir "$out"
out=$(cd "$out" && pwd -P)
mkdir "$out/original" "$out/patched" "$out/provider" "$out/consumer"
tar -xf "$archive" -C "$out/original" --strip-components 1 \
    fcitx5-5.1.23/src/lib fcitx5-5.1.23/src/modules/emoji/emoji_public.h
cp -R "$out/original/" "$out/patched/"
cp "$recipe/tests/cmake-export-provider.cmake" "$out/provider/CMakeLists.txt"
cp "$recipe/tests/cmake-export-consumer.cmake" "$out/consumer/CMakeLists.txt"
for item in patch-src_lib_fcitx-utils_CMakeLists.txt patch-src_lib_fcitx-config_CMakeLists.txt \
    patch-src_lib_fcitx_CMakeLists.txt patch-src_lib_fcitx-utils_Fcitx5Macros.cmake \
    patch-src_lib_fcitx-utils_Fcitx5ModuleTemplate.cmake.in; do
    actual=$(sed '/[$]NetBSD.*/d' "$recipe/patches/$item" | shasum | awk '{print $1}')
    expected=$(awk -v name="($item)" '$1 == "SHA1" && $2 == name {print $4}' "$recipe/distinfo")
    [ "$actual" = "$expected" ]
    patch -s -F0 -d "$out/patched" -p0 < "$recipe/patches/$item"
done
consume() {
    "$CMAKE" -S "$out/consumer" -B "$1" "-DCMAKE_PREFIX_PATH=$2" \
        "-DEXPECTED_PREFIX=$2" "-DMODULE_ONLY=${3:-OFF}" -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF \
        -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF
}
# Read-only control against the real previously installed package exports.
if consume "$out/installed-before" "$installed" > "$out/installed-before.log" 2>&1; then
    echo 'Installed baseline unexpectedly relocatable; use the unfixed baseline' >&2; exit 1
fi
grep -q 'Non-relocatable Utils includes' "$out/installed-before.log"
for mode in original patched; do
    "$CMAKE" -S "$out/provider" -B "$out/$mode-build" \
        "-DFCITX_SOURCE=$out/$mode" -DCMAKE_INSTALL_PREFIX=/opt/fcitx-export-check \
        > "$out/$mode-configure.log" 2>&1
    env DESTDIR="$out/$mode-stage" "$CMAKE" --install "$out/$mode-build" \
        > "$out/$mode-install.log" 2>&1
    prefix=$out/$mode-stage/opt/fcitx-export-check
    if [ "$mode" = original ]; then
        if consume "$out/original-destdir" "$prefix" > "$out/original-destdir.log" 2>&1; then exit 1; fi
        grep -q 'Non-relocatable Utils includes' "$out/original-destdir.log"
        if consume "$out/original-module" "$prefix" ON > "$out/original-module.log" 2>&1; then exit 1; fi
        grep -q 'Non-relocatable module includes' "$out/original-module.log"
    else
        consume "$out/patched-destdir" "$prefix" > "$out/patched-destdir.log" 2>&1
    fi
    mv "$prefix" "$out/$mode-relocated"
    if [ "$mode" = original ]; then
        if consume "$out/original-moved" "$out/original-relocated" > "$out/original-moved.log" 2>&1; then exit 1; fi
        grep -q 'Non-relocatable Utils includes' "$out/original-moved.log"
    else
        consume "$out/patched-moved" "$out/patched-relocated" > "$out/patched-moved.log" 2>&1
    fi
done
printf 'PASS: actual installed baseline fails; original library and module exports fail; DESTDIR/move; patched Utils/Config/Core/Emoji headers relocate.\n'
printf 'The fixture executes source install-interface expressions and the real module macro. No compiler, target program, or full library build ran.\n'
