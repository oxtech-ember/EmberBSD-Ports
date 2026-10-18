#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
set -eu
umask 022
[ "$#" = 4 ] || { echo 'Usage: configure-cross.sh ABS_SOURCE ABS_SYSROOT ABS_TOOLCHAIN_CMAKE ABS_NEW_BUILD' >&2; exit 2; }
source=$1
sysroot=$2
toolchain=$3
build=$4
: "${CC:?Set CC to the common target GCC16 compiler or wrapper.}"
: "${CXX:?Set CXX to the common target GCC16 C++ compiler or wrapper.}"
: "${HOST_PYTHON:?Set HOST_PYTHON to the installed native Python 3.15 executable.}"
: "${HOST_SWIG:?Set HOST_SWIG to the installed native SWIG 4.5.1 executable.}"
: "${HOST_PROTOC:?Set HOST_PROTOC to native protoc from the target Protobuf release.}"
: "${TARGET_WX_CONFIG:?Set TARGET_WX_CONFIG to the installed target wx-config script.}"
: "${PKG_CONFIG:?Set PKG_CONFIG to the target-scoped pkg-config wrapper.}"
profile=${KICAD_PROFILE:-upstream}
case "$profile" in
    pkgsrc) wxpython=OFF ;;
    upstream)
        echo 'The upstream profile keeps wxPython ON. KiCad 10.0.7 queries host wxPython during cross configuration.' >&2
        echo 'Target wxPython discovery must be ported before using this profile. No feature was disabled.' >&2
        exit 2 ;;
    *) echo 'KICAD_PROFILE must be upstream or pkgsrc.' >&2; exit 2 ;;
esac
for path in "$source" "$sysroot" "$toolchain" "$build" "$CC" "$CXX" "$HOST_PYTHON" "$HOST_SWIG" "$HOST_PROTOC" "$TARGET_WX_CONFIG" "$PKG_CONFIG"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without whitespace or shell metacharacters.' >&2; exit 2 ;; esac
done
[ ! -e "$build" ] && [ ! -L "$build" ] || { echo 'Build path already exists.' >&2; exit 2; }
for file in "$toolchain" "$TARGET_WX_CONFIG" "$source/.ember-source-pin" "$source/CMakeLists.txt" "$source/qa/CMakeLists.txt" "$source/demos/CMakeLists.txt" "$source/api/CMakeLists.txt" "$source/pcbnew/python/swig/pcbnew.i" "$sysroot/usr/pkg/include/python3.15/Python.h" "$sysroot/usr/pkg/lib/libpython3.15.so"; do
    [ -f "$file" ] || { echo "Missing required input: $file" >&2; exit 2; }
done
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cmp "$source/.ember-source-pin" "$here/sources.tsv" || { echo 'Source pin does not match this recipe.' >&2; exit 2; }
for executable in "$CC" "$CXX" "$HOST_PYTHON" "$HOST_SWIG" "$HOST_PROTOC" "$PKG_CONFIG"; do
    [ -x "$executable" ] || { echo "Not executable: $executable" >&2; exit 2; }
done
for tool in cmake ninja ruby; do command -v "$tool" >/dev/null; done
unset LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH PKG_CONFIG_PATH
PKG_CONFIG_SYSROOT_DIR=$sysroot
PKG_CONFIG_LIBDIR=$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/pkg/share/pkgconfig:$sysroot/usr/lib/pkgconfig:$sysroot/usr/share/pkgconfig
export PKG_CONFIG_SYSROOT_DIR PKG_CONFIG_LIBDIR
mkdir "$build"
mkdir "$build/ember-logs"
run()
{
    name=$1
    shift
    status=0
    "$@" > "$build/ember-logs/$name.log" 2>&1 || status=$?
    if [ "$status" -ne 0 ]; then
        cat "$build/ember-logs/$name.log" >&2
        exit "$status"
    fi
}
run toolchain cmake -DEMBER_TOOLCHAIN="$toolchain" -DEMBER_SYSROOT="$sysroot" \
    -DEMBER_CC="$CC" -DEMBER_CXX="$CXX" -P "$here/check-toolchain.cmake"
run c-macros "$CC" --sysroot="$sysroot" -dM -E -x c /dev/null
run cxx-macros "$CXX" --sysroot="$sysroot" -dM -E -x c++ /dev/null
ruby -e 'ARGV.each { |p| s=File.read(p); abort "Expected real AArch64 NetBSD GCC16 macros" unless s.match?(/^#define __GNUC__ 16$/) && s.match?(/^#define __aarch64__ /) && s.match?(/^#define __NetBSD__ /) && !s.match?(/^#define __clang__ /) }' "$build/ember-logs/c-macros.log" "$build/ember-logs/cxx-macros.log"
run python-version "$HOST_PYTHON" --version
run swig-version "$HOST_SWIG" -version
run protoc-version "$HOST_PROTOC" --version
run protobuf-version "$PKG_CONFIG" --modversion protobuf
run protobuf-sysroot "$PKG_CONFIG" --variable=pc_sysrootdir protobuf
ruby -e 'abort "Native Python 3.15 is required" unless File.read(ARGV[0]).match?(/^Python 3\.15\./); abort "Native SWIG 4.5.1 is required" unless File.read(ARGV[1]).match?(/^SWIG Version 4\.5\.1$/); abort "pkg-config is not scoped to the requested sysroot" unless File.read(ARGV[2]).strip == ARGV[3]' "$build/ember-logs/python-version.log" "$build/ember-logs/swig-version.log" "$build/ember-logs/protobuf-sysroot.log" "$sysroot"
run pkg-config "$PKG_CONFIG" --print-errors --exists gtk+-3.0 webkit2gtk-4.1 gl glu egl ngspice python-3.15-embed
run wx-version sh "$TARGET_WX_CONFIG" --prefix="$sysroot/usr/pkg" --exec-prefix="$sysroot/usr/pkg" --static=no --toolkit=gtk3 --version
run wx-libraries sh "$TARGET_WX_CONFIG" --prefix="$sysroot/usr/pkg" --exec-prefix="$sysroot/usr/pkg" --static=no --toolkit=gtk3 --libs gl,aui,adv,html,core,net,base,propgrid,xml,stc,richtext,webview
printf '%s\n' "$profile" > "$build/ember-logs/profile.txt"
run configure cmake -S "$source" -B "$build" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$toolchain" \
    -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" \
    -DCMAKE_SYSROOT="$sysroot" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/usr/pkg -DCMAKE_PREFIX_PATH=/usr/pkg \
    '-DCMAKE_INSTALL_RPATH=/usr/pkg/gcc16/lib;/usr/pkg/lib' \
    -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=OFF -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DPKG_CONFIG_EXECUTABLE="$PKG_CONFIG" \
    -DPYTHON_EXECUTABLE="$HOST_PYTHON" \
    -DPYTHON_LIBRARY="$sysroot/usr/pkg/lib/libpython3.15.so" \
    -DPYTHON_INCLUDE_DIR="$sysroot/usr/pkg/include/python3.15" \
    -DPYTHON_SITE_PACKAGE_PATH=lib/python3.15/site-packages \
    -DSWIG_EXECUTABLE="$HOST_SWIG" \
    -DProtobuf_PROTOC_EXECUTABLE="$HOST_PROTOC" \
    -DwxWidgets_CONFIG_EXECUTABLE="$TARGET_WX_CONFIG" \
    "-DwxWidgets_CONFIG_OPTIONS=--prefix=$sysroot/usr/pkg;--exec-prefix=$sysroot/usr/pkg;--toolkit=gtk3" \
    -DKICAD_SCRIPTING_WXPYTHON="$wxpython" \
    -DKICAD_IPC_API=ON -DKICAD_BUILD_QA_TESTS=ON -DKICAD_SPICE_QA=ON \
    -DKICAD_SIGNAL_INTEGRITY=ON -DKICAD_WAYLAND=ON -DKICAD_BUILD_I18N=ON
printf 'Configured KiCad. Build, install and target acceptance remain separate steps: %s\n' "$build"
