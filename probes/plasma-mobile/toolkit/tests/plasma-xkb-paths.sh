#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run Plasma's actual XKB configure lookup.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 PLASMA_DESKTOP_SOURCE NEW_OUTPUT" >&2; exit 2; }
: "${CMAKE:?Set native CMake}"
: "${PKG_CONFIG:?Set native pkgconf}"
source=$(CDPATH= cd -- "$1" && pwd)
tests=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
mkdir -p "$work/original" "$work/patched" "$work/project" "$work/pc" \
    "$work/root/usr/pkg/share/X11/xkb" "$work/root-sibling/usr/pkg/share/X11/xkb" \
    "$work/native/share/X11/xkb"
cp "$source/ConfigureChecks.cmake" "$work/original/ConfigureChecks.cmake"
cp "$source/ConfigureChecks.cmake" "$work/patched/ConfigureChecks.cmake"
cp "$source/config-workspace.h.cmake" "$work/config-workspace.h.cmake"
patch -d "$work/patched" -p0 < \
    "$tests/../recipes/x11/plasma6-plasma-desktop/patches/patch-ConfigureChecks.cmake" \
    > "$work/patch.log"
# Execute the complete production lookup. Exclude the unrelated compiler probes.
for tree in original patched; do
    awk '/^check_function_exists\(statvfs HAVE_STATVFS\)/ { found=1; exit }
        { print }
        END { if (!found) exit 1 }' "$work/$tree/ConfigureChecks.cmake" \
        > "$work/$tree/xkb-check.cmake"
done
cat > "$work/project/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.16)
project(PlasmaXkbLookup NONE)
find_package(PkgConfig REQUIRED)
include("${LOOKUP_SOURCE}")
if(NOT XKBDIR STREQUAL EXPECTED_XKBDIR)
    message(FATAL_ERROR "Unexpected runtime XKBDIR: ${XKBDIR}")
endif()
configure_file("${WORKSPACE_TEMPLATE}" config-workspace.h)
file(READ "${CMAKE_CURRENT_BINARY_DIR}/config-workspace.h" header)
string(FIND "${header}" "#define XKBDIR \"${EXPECTED_XKBDIR}\"" header_at)
if(header_at EQUAL -1)
    message(FATAL_ERROR "The generated header does not contain the target XKB path.")
endif()
CMAKE
"$CMAKE" --version > "$work/cmake-version.txt"
"$PKG_CONFIG" --version > "$work/pkgconf-version.txt"
export PKG_CONFIG_LIBDIR="$work/pc"
export PKG_CONFIG_PATH=
export PKG_CONFIG_ALLOW_SYSTEM_CFLAGS=1
export PKG_CONFIG_ALLOW_SYSTEM_LIBS=1
count=0
run_case() {
    name=$1 tree=$2 mode=$3 value=$4 sysroot=$5 pkgroot=$6 expected=$7 outcome=$8 diagnostic=$9
    cat > "$work/pc/xkeyboard-config.pc" <<EOF
xkb_base=$value
Name: XKeyboardConfig
Description: Plasma configure regression fixture
Version: 2.48
EOF
    if [ "$#" -ge 10 ]; then
        printf 'xkb_root=%s\n' "${10}" >> "$work/pc/xkeyboard-config.pc"
    fi
    export PKG_CONFIG_SYSROOT_DIR="$pkgroot"
    "$PKG_CONFIG" --variable=xkb_base xkeyboard-config > "$work/$name-variable.txt"
    set -- -S "$work/project" -B "$work/$name" \
        "-DPKG_CONFIG_EXECUTABLE=$PKG_CONFIG" \
        "-DLOOKUP_SOURCE=$work/$tree/xkb-check.cmake" \
        "-DWORKSPACE_TEMPLATE=$work/config-workspace.h.cmake" \
        "-DEXPECTED_XKBDIR=$expected"
    if [ "$mode" = cross ]; then
        set -- "$@" -DCMAKE_SYSTEM_NAME=NetBSD "-DCMAKE_SYSROOT=$sysroot"
    fi
    if "$CMAKE" "$@" > "$work/$name.log" 2>&1; then
        [ "$outcome" = pass ] || { echo "FAIL: $name accepted invalid lookup" >&2; exit 1; }
    else
        [ "$outcome" = fail ] || { cat "$work/$name.log" >&2; exit 1; }
        grep -F -q "$diagnostic" "$work/$name.log" || {
            echo "FAIL: $name did not report the expected cause" >&2; exit 1;
        }
    fi
    count=$((count + 1))
    printf 'PASS: %s\n' "$name"
}
target=/usr/pkg/share/X11/xkb
native=$work/native/share/X11/xkb
run_case original-native original native "$native" '' '' "$native" pass ''
run_case original-prefixed original cross "$target" "$work/root" "$work/root" "$target" fail \
    "Couldn't find XKB location in CMAKE_SYSROOT"
# Make the original failure causal: real pkgconf must have supplied the prefix.
[ "$(cat "$work/original-prefixed-variable.txt")" = "$work/root$target" ] || {
    echo 'FAIL: this pkg-config implementation did not reproduce sysroot prefixing' >&2; exit 1;
}
run_case patched-native patched native "$native" '' '' "$native" pass ''
run_case cross-plain patched cross "$target" "$work/root" '' "$target" pass ''
run_case cross-prefixed patched cross "$target" "$work/root" "$work/root" "$target" pass ''
run_case cross-normalized-root patched cross "$target" "$work/root/../root/" "$work/root" "$target" pass ''
run_case cross-slash-root patched cross "$native" / '' "$native" pass ''
run_case cross-missing patched cross /usr/pkg/share/missing-xkb "$work/root" "$work/root" /usr/pkg/share/missing-xkb fail \
    "Couldn't find XKB location in CMAKE_SYSROOT"
run_case cross-host-fallback patched cross "$native" "$work/root" '' "$native" fail \
    "Couldn't find XKB location in CMAKE_SYSROOT"
run_case cross-prefix-boundary patched cross "$work/root-sibling$target" "$work/root" '' "$target" fail \
    "Couldn't find XKB location in CMAKE_SYSROOT"
run_case cross-empty-root patched cross "$target" '' '' "$target" fail \
    'Cross XKB lookup requires an absolute CMAKE_SYSROOT'
run_case native-relative patched native share/X11/xkb '' '' share/X11/xkb fail \
    'XKB location must be absolute'
run_case native-missing patched native "$work/missing" '' '' "$work/missing" fail \
    "Couldn't find XKB location:"
printf 'not a directory\n' > "$work/not-a-directory"
run_case native-file patched native "$work/not-a-directory" '' '' "$work/not-a-directory" fail \
    "Couldn't find XKB location:"
# Current xkeyboard-config installs a target-absolute compatibility alias.
canonical=/usr/pkg/share/xkeyboard-config-2
mkdir -p "$work/modern-root$canonical" "$work/modern-root/usr/pkg/share/X11" \
    "$work/native/share/xkeyboard-config-2"
ln -s "$canonical" "$work/modern-root$target"
[ -L "$work/modern-root$target" ] && [ ! -d "$work/modern-root$target" ] || {
    echo 'The absolute target alias unexpectedly resolves on this host' >&2; exit 1;
}
run_case original-absolute-alias original cross "$target" "$work/modern-root" '' "$target" fail \
    "Couldn't find XKB location in CMAKE_SYSROOT" "$canonical"
run_case modern-plain patched cross "$target" "$work/modern-root" '' "$canonical" pass '' "$canonical"
run_case modern-prefixed patched cross "$target" "$work/modern-root" "$work/modern-root" "$canonical" pass '' "$canonical"
run_case modern-root-only patched cross '' "$work/modern-root" "$work/modern-root" "$canonical" pass '' "$canonical"
run_case modern-native patched native "$native" '' '' "$work/native/share/xkeyboard-config-2" pass '' \
    "$work/native/share/xkeyboard-config-2"
# A declared but invalid canonical root must not be hidden by the legacy data.
run_case modern-missing patched cross "$target" "$work/root" '' /usr/pkg/share/missing-xkb fail \
    "Couldn't find XKB location in CMAKE_SYSROOT" /usr/pkg/share/missing-xkb
run_case modern-relative patched cross "$target" "$work/root" '' share/xkb fail \
    'XKB location must be absolute' share/xkb
printf 'PASS: %s real Plasma/pkgconf lookup cases\n' "$count"
