#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check installed data paths without target execution.
set -eu
[ "$#" = 4 ] || {
    echo "Usage: $0 PKGSRC MAKECONF SOURCE_ARCHIVE NEW_OUTPUT" >&2
    exit 2
}
: "${BMAKE:?Set native bmake}" "${CMAKE:?Set native CMake}"
pkgsrc=$1 conf=$2 archive=$3 out=$4
for item in "$@" "$BMAKE" "$CMAKE"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
recipe=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
sha256=$(shasum -a 256 "$archive" | awk '{print $1}')
[ "$sha256" = d287119db9dc3113bb3a2b0e78ce8670e064b744c14d3aaec69799374aadb00b ]
mkdir "$out"
out=$(cd "$out" && pwd -P)
mkdir "$out/original" "$out/patched" "$out/patched/cmake"
for item in CMakeLists.txt config.h.in data/CMakeLists.txt; do
    mkdir -p "$out/original/$(dirname "$item")" "$out/patched/$(dirname "$item")"
    tar -xOf "$archive" "fcitx5-5.1.23/$item" > "$out/original/$item"
    cp "$out/original/$item" "$out/patched/$item"
done
for item in patch-CMakeLists.txt patch-config.h.in patch-cmake_Fcitx5RuntimeDataPaths.cmake; do
    actual=$(sed '/^\$NetBSD/d' "$recipe/patches/$item" | shasum | awk '{print $1}')
    expected=$(awk -v name="($item)" '$1 == "SHA1" && $2 == name { print $4 }' "$recipe/distinfo")
    [ "$actual" = "$expected" ]
    patch -s -F 0 -d "$out/patched" -p0 < "$recipe/patches/$item"
done
# Exercise the real runtime-path module and config.h template. Discovery values
# remain host-readable paths. They must not be overwritten by installed paths.
cat > "$out/check.cmake" <<'CMAKE'
set(host "$ENV{CHECK_ROOT}/sysroot/usr/pkg/share")
set(ISOCODES_ISO639_JSON "${host}/iso-codes/json/iso_639-3.json")
set(XKEYBOARDCONFIG_XKBBASE "${host}/X11/xkb")
set(XKEYBOARDCONFIG_DATADIR "${host}")
if(NOT "$ENV{CHECK_MODE}" STREQUAL "native")
    set(ISOCODES_ISO639_JSON_RUNTIME "/usr/pkg/share/iso-codes/json/iso_639-3.json")
    set(XKEYBOARDCONFIG_XKBBASE_RUNTIME "/usr/pkg/share/X11/xkb")
    set(XKEYBOARDCONFIG_DATADIR_RUNTIME "/usr/pkg/share")
endif()
if(NOT "$ENV{CHECK_MODE}" STREQUAL "original")
    include("$ENV{CHECK_ROOT}/patched/cmake/Fcitx5RuntimeDataPaths.cmake")
endif()
foreach(variable ISOCODES_ISO639_JSON XKEYBOARDCONFIG_XKBBASE XKEYBOARDCONFIG_DATADIR)
    string(FIND "${${variable}}" "${host}" index)
    if(NOT index EQUAL 0)
        message(FATAL_ERROR "Configure discovery path changed: ${variable}")
    endif()
    if(NOT EXISTS "${${variable}}")
        message(FATAL_ERROR "Host discovery file missing: ${variable}")
    endif()
endforeach()
if("$ENV{CHECK_MODE}" STREQUAL "original")
    set(template "$ENV{CHECK_ROOT}/original/config.h.in")
else()
    set(template "$ENV{CHECK_ROOT}/patched/config.h.in")
endif()
configure_file("${template}" "$ENV{CHECK_ROOT}/$ENV{CHECK_MODE}.h")
file(READ "$ENV{CHECK_ROOT}/$ENV{CHECK_MODE}.h" config)
foreach(variable ISOCODES_ISO639_JSON XKEYBOARDCONFIG_XKBBASE XKEYBOARDCONFIG_DATADIR)
    string(FIND "${config}" "#define ${variable} \"${${variable}_RUNTIME}\"" index)
    if(index EQUAL -1)
        message(FATAL_ERROR "Runtime path mismatch: ${variable}")
    endif()
endforeach()
CMAKE
mkdir -p "$out/sysroot/usr/pkg/share/iso-codes/json" "$out/sysroot/usr/pkg/share/X11/xkb/rules"
printf '{}\n' > "$out/sysroot/usr/pkg/share/iso-codes/json/iso_639-3.json"
printf '<xkbConfigRegistry/>\n' > "$out/sysroot/usr/pkg/share/X11/xkb/rules/evdev.xml"
if env CHECK_ROOT="$out" CHECK_MODE=original "$CMAKE" -P "$out/check.cmake" > "$out/original.log" 2>&1; then
    echo 'Original source did not reproduce the runtime path leak' >&2; exit 1
fi
grep -q 'Runtime path mismatch' "$out/original.log"
for mode in native cross; do
    env CHECK_ROOT="$out" CHECK_MODE="$mode" "$CMAKE" -P "$out/check.cmake" > "$out/$mode.log" 2>&1
done
mv "$out/sysroot/usr/pkg/share/iso-codes/json/iso_639-3.json" "$out/iso_639-3.json"
if env CHECK_ROOT="$out" CHECK_MODE=cross "$CMAKE" -P "$out/check.cmake" > "$out/missing.log" 2>&1; then
    echo 'Missing host data incorrectly accepted' >&2; exit 1
fi
grep -q 'Host discovery file missing' "$out/missing.log"
for mode in no yes; do
    "$BMAKE" -C "$pkgsrc/inputmethod/fcitx5" -f "$recipe/Makefile" \
        MAKECONF="$conf" USE_CROSS_COMPILE="$mode" WRKOBJDIR="$out/work" \
        -v PKG_FAIL_REASON -v CMAKE_CONFIGURE_ARGS -v CONF_FILES -v MAKE_DIRS -v SUBST_SED.xdg -v PREFIX \
        > "$out/$mode.raw"
    awk 'BEGIN {split("FAIL ARGS CONF DIRS SUBST PREFIX", names)} {print names[NR] "=" $0}' "$out/$mode.raw" > "$out/$mode.metadata"
    grep -q '^FAIL=$' "$out/$mode.metadata"
    prefix=$(sed -n 's/^PREFIX=//p' "$out/$mode.metadata")
    for arg in "-DISOCODES_ISO639_JSON_RUNTIME:FILEPATH=$prefix/share/iso-codes/json/iso_639-3.json" \
               "-DXKEYBOARDCONFIG_XKBBASE_RUNTIME:PATH=$prefix/share/X11/xkb" \
               "-DXKEYBOARDCONFIG_DATADIR_RUNTIME:PATH=$prefix/share"; do
        grep '^ARGS=' "$out/$mode.metadata" | grep -F -- "$arg" >/dev/null
    done
    grep '^CONF=' "$out/$mode.metadata" | tr -s ' ' | grep -F "$prefix/share/examples/fcitx5/20-fcitx-x11 $prefix/etc/xdg/Xwayland-session.d/20-fcitx-x11" >/dev/null
    grep '^DIRS=' "$out/$mode.metadata" | grep -F "$prefix/etc/xdg/Xwayland-session.d" >/dev/null
    grep '^SUBST=' "$out/$mode.metadata" | grep -F '{CMAKE_INSTALL_FULL_SYSCONFDIR}/xdg/Xwayland-session.d,{CMAKE_INSTALL_PREFIX}/share/examples/fcitx5' >/dev/null
done
printf 'PASS: original leak reproduced; fixed native/cross paths; host discovery values preserved; missing host fixture detected (contract check); native/cross recipe metadata.\n'
printf 'No C/C++ compilation, source analysis, or target execution is claimed.\n'
