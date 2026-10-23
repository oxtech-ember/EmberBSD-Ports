#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check data paths without target execution.
set -eu
[ "$#" = 4 ] || {
    echo "Usage: $0 PKGSRC MAKECONF SOURCE_ARCHIVE NEW_OUTPUT" >&2
    exit 2
}
: "${BMAKE:?Set native bmake}" "${CMAKE:?Set native CMake}"
: "${PKG_CONFIG:=pkg-config}"
pkgsrc=$1 conf=$2 archive=$3 out=$4
for item in "$@" "$BMAKE" "$CMAKE"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
recipe=$(dirname "$here")
sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    elif command -v sha256 >/dev/null 2>&1; then sha256 -q "$1"
    else shasum -a 256 "$1" | awk '{print $1}'
    fi
}
[ "$(sha256 "$archive")" = 0d9b9e023d3aa7056ec185ed9e6ccfb94e5a5b930d3dd742dba7f37a49abd61e ]
[ ! -e "$out" ] && [ ! -L "$out" ]
mkdir "$out"
out=$(cd "$out" && pwd -P)
tar -xf "$archive" -C "$out"
mv "$out/fcitx5-configtool-5.1.16" "$out/original"
cp -R "$out/original" "$out/patched"
for item in "$recipe"/patches/patch-*; do
    name=${item##*/}
    actual=$(sed '/[$]NetBSD.*/d' "$item" | shasum -a 1 | awk '{print $1}')
    expected=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name { print $4 }' "$recipe/distinfo")
    [ "$actual" = "$expected" ]
    patch -f -N -F 0 -d "$out/patched" -p0 < "$item"
done
mkdir "$out/harness"
cp "$here/runtime-data-paths.cmake" "$out/harness/CMakeLists.txt"
pc=$(command -v "$PKG_CONFIG")

fixture() {
    root=$1 prefix=$2
    host=$root$prefix
    mkdir -p "$host/share/pkgconfig" "$host/share/iso-codes/json" "$host/share/X11/xkb/rules"
    for code in 2 3 5; do printf '{}\n' > "$host/share/iso-codes/json/iso_639-$code.json"; done
    printf '<xkbConfigRegistry/>\n' > "$host/share/X11/xkb/rules/evdev.xml"
    cat > "$host/share/pkgconfig/iso-codes.pc" <<PC
prefix=$prefix
Name: iso-codes
Description: Controlled discovery fixture
Version: 4.20.1
PC
    cat > "$host/share/pkgconfig/xkeyboard-config.pc" <<PC
prefix=$prefix
datadir=\${prefix}/share
xkb_base=\${datadir}/X11/xkb
Name: xkeyboard-config
Description: Controlled discovery fixture
Version: 2.45
PC
}
configure() {
    name=$1 source=$2 patched=$3 root=$4 prefix=$5
    shift 5
    env PKG_CONFIG_PATH= PKG_CONFIG_LIBDIR="$root$prefix/share/pkgconfig" \
        PKG_CONFIG_SYSROOT_DIR="$root" "$CMAKE" -S "$out/harness" -B "$out/$name" \
        "-DPKG_CONFIG_EXECUTABLE:FILEPATH=$pc" "-DSOURCE:PATH=$source" \
        "-DPATCHED:BOOL=$patched" "-DHOST_PREFIX:PATH=$root$prefix" \
        "-DRUNTIME_PREFIX:PATH=$prefix" "-DCMAKE_FIND_ROOT_PATH:PATH=$root" \
        -DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY "$@" > "$out/$name.log" 2>&1
}
fixture "" "$out/native-prefix"
configure native-original "$out/original" OFF "" "$out/native-prefix"
configure native-patched "$out/patched" ON "" "$out/native-prefix"
for mode in cross custom; do
    case "$mode" in cross) prefix=/usr/pkg ;; custom) prefix=/opt/ember-test ;; esac
    root=$out/$mode-root
    fixture "$root" "$prefix"
    set --
    for code in 2 3 5; do
        set -- "$@" "-DISOCODES_ISO639_${code}_JSON_RUNTIME:FILEPATH=$prefix/share/iso-codes/json/iso_639-$code.json"
    done
    set -- "$@" "-DXKEYBOARDCONFIG_XKBBASE_RUNTIME:PATH=$prefix/share/X11/xkb"
    if configure "$mode-original" "$out/original" OFF "$root" "$prefix" "$@"; then
        echo 'Original source did not reproduce the runtime path leak' >&2; exit 1
    fi
    grep -q 'Runtime path mismatch' "$out/$mode-original.log"
    configure "$mode-patched" "$out/patched" ON "$root" "$prefix" "$@"
    mv "$root$prefix/share/iso-codes/json/iso_639-3.json" "$root/moved.json"
    if configure "$mode-missing" "$out/patched" ON "$root" "$prefix" "$@"; then
        echo 'Missing discovery data incorrectly accepted' >&2; exit 1
    fi
    grep -q 'Could NOT find IsoCodes' "$out/$mode-missing.log"
    mv "$root/moved.json" "$root$prefix/share/iso-codes/json/iso_639-3.json"
done

# Run the exact production include statement against a resolved package location.
# The marker represents the included CMake module, not a target runtime binary.
mkdir -p "$out/compiler-package"
printf 'set(COMPILER_SETTINGS_LOADED TRUE)\n' > "$out/compiler-package/Fcitx5CompilerSettings.cmake"
for mode in original patched; do
    {
        printf 'set(FCITX_INSTALL_CMAKECONFIG_DIR "%s/absent-target")\n' "$out"
        printf 'set(Fcitx5Utils_DIR "%s/compiler-package")\n' "$out"
        awk '/^include\(.*Fcitx5CompilerSettings[.]cmake/ {print; count++} END {if (count != 1) exit 1}' "$out/$mode/CMakeLists.txt"
        printf 'if(NOT COMPILER_SETTINGS_LOADED)\n message(FATAL_ERROR "Compiler module not loaded")\nendif()\n'
    } > "$out/$mode-compiler.cmake"
    if "$CMAKE" -P "$out/$mode-compiler.cmake" > "$out/$mode-compiler.log" 2>&1; then
        [ "$mode" = patched ]
    else
        [ "$mode" = original ]
        grep -q 'include could not find requested file' "$out/$mode-compiler.log"
    fi
done

for mode in no yes; do
    "$BMAKE" -C "$pkgsrc/inputmethod/fcitx5-configtool" -f "$recipe/Makefile" \
        MAKECONF="$conf" USE_CROSS_COMPILE="$mode" WRKOBJDIR="$out/work" \
        -v PKG_FAIL_REASON -v CMAKE_CONFIGURE_ARGS -v PREFIX -v TOOLS_PATH.msgfmt -v TOOLS_PATH.msgmerge \
        > "$out/$mode.raw"
    awk 'BEGIN {split("FAIL ARGS PREFIX MSGFMT MSGMERGE", names)} {print names[NR] "=" $0}' "$out/$mode.raw" > "$out/$mode.metadata"
    grep -q '^FAIL=$' "$out/$mode.metadata"
    prefix=$(sed -n 's/^PREFIX=//p' "$out/$mode.metadata")
    for code in 2 3 5; do
        grep '^ARGS=' "$out/$mode.metadata" | grep -F -- "-DISOCODES_ISO639_${code}_JSON_RUNTIME:FILEPATH=$prefix/share/iso-codes/json/iso_639-$code.json" >/dev/null
    done
    grep '^ARGS=' "$out/$mode.metadata" | grep -F -- "-DXKEYBOARDCONFIG_XKBBASE_RUNTIME:PATH=$prefix/share/X11/xkb" >/dev/null
    for tool in MSGFMT MSGMERGE; do
        path=$(sed -n "s/^$tool=//p" "$out/$mode.metadata")
        [ -n "$path" ]
        grep '^ARGS=' "$out/$mode.metadata" | grep -F -- "-DGETTEXT_${tool}_EXECUTABLE:FILEPATH=$path" >/dev/null
    done
done
"$BMAKE" -C "$pkgsrc/inputmethod/fcitx5-configtool" -f "$recipe/Makefile" \
    MAKECONF="$conf" USE_CROSS_COMPILE=yes WRKOBJDIR="$out/work" \
    BUILDLINK_PREFIX.iso-codes=/opt/ember-iso BUILDLINK_PREFIX.xkeyboard-config=/opt/ember-xkb \
    -v CMAKE_CONFIGURE_ARGS > "$out/provider-prefix.metadata"
for code in 2 3 5; do
    grep -F -- "-DISOCODES_ISO639_${code}_JSON_RUNTIME:FILEPATH=/opt/ember-iso/share/iso-codes/json/iso_639-$code.json" "$out/provider-prefix.metadata" >/dev/null
done
grep -F -- '-DXKEYBOARDCONFIG_XKBBASE_RUNTIME:PATH=/opt/ember-xkb/share/X11/xkb' "$out/provider-prefix.metadata" >/dev/null
printf 'PASS: real Find modules, native defaults, cross and custom-prefix paths, original failure controls, missing-data rejection, resolved compiler-module include, native Gettext tools and provider-prefix recipe metadata.\n'
printf 'No complete application build, target execution or C/C++ analysis is claimed.\n'
