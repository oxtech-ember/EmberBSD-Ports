#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the selected LibIntl header provider.
set -eu
[ "$#" = 5 ] || {
    echo "Usage: $0 PKGSRC MAKECONF FCITX_RECIPE FCITX_SOURCE NEW_OUTPUT" >&2
    exit 2
}
: "${BMAKE:?Set native bmake}" "${CMAKE:?Set native CMake}" \
    "${NINJA:?Set native Ninja}" "${NATIVE_CC:?Set native C compiler}" \
    "${CROSS_CC:?Set the configured cross C compiler}"
pkgsrc=$1 conf=$2 recipe=$3 source=$4 out=$5
NATIVE_AR=${NATIVE_AR:-$(command -v ar)}
for path in "$@" "$BMAKE" "$CMAKE" "$NINJA" "$NATIVE_CC" "$CROSS_CC" "$NATIVE_AR"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
fail() { echo "FAIL: $*" >&2; exit 1; }
field() { sed -n "s/^$1=//p" "$2"; }
mkdir "$out"
mkdir "$out/fixture"
cat > "$out/fixture/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.19)
project(FcitxLibIntlHeaders C)
list(PREPEND CMAKE_MODULE_PATH "$ENV{FCITX_SOURCE}/cmake")
find_package(LibIntl REQUIRED)
get_target_property(intl_include LibIntl::LibIntl INTERFACE_INCLUDE_DIRECTORIES)
get_target_property(intl_library LibIntl::LibIntl IMPORTED_LOCATION)
file(WRITE "${CMAKE_BINARY_DIR}/imported-target.txt"
    "include=${intl_include}\nlibrary=${intl_library}\n")
# An existing directory does not prove that it supplies the selected header.
# Without this check, the compiler can silently fall back to base libintl.h.
if(NOT EXISTS "${intl_include}/libintl.h")
    message(FATAL_ERROR "LibIntl imported target does not provide libintl.h")
endif()
add_library(header-consumer OBJECT consumer.c)
target_link_libraries(header-consumer PRIVATE LibIntl::LibIntl)
if(EXPECT_PACKAGE_GETTEXT)
    target_compile_definitions(header-consumer PRIVATE EXPECT_PACKAGE_GETTEXT=1)
endif()
CMAKE
cat > "$out/fixture/consumer.c" <<'C'
#include <libintl.h>
#if defined(EXPECT_PACKAGE_GETTEXT) && !defined(__USE_GNU_GETTEXT)
#error "The package LibIntl target selected a base gettext header."
#endif
const char *
fcitx_header_consumer(const char *message)
{
    return dgettext("fcitx5", message);
}
C
FCITX_SOURCE=$source
export FCITX_SOURCE
for variant in cross-base cross-package native-package; do
    case "$variant" in
        cross-base) mode=yes; prefer=native; builtin=yes; cc=$CROSS_CC ;;
        cross-package) mode=yes; prefer=pkgsrc; builtin=no; cc=$CROSS_CC ;;
        native-package) mode=no; prefer=pkgsrc; builtin=no; cc=$NATIVE_CC ;;
    esac
    result=$out/$variant
    mkdir "$result"
    # Prefixes are initialized after the pkgsrc barrier, as for configure.
    # Read-only -V calls without this barrier can show uninitialized prefixes.
    "$BMAKE" -C "$pkgsrc/inputmethod/fcitx5" -f "$recipe/Makefile" \
        MAKECONF="$conf" USE_CROSS_COMPILE="$mode" PREFER.gettext="$prefer" \
        WRKDIR="$result/work" _PKGSRC_BARRIER=yes \
        -V 'FAIL=${PKG_FAIL_REASON}' -V 'BUILTIN=${USE_BUILTIN.gettext}' \
        -V 'PREFIX=${BUILDLINK_PREFIX.gettext}' -V 'LINKS=${BUILDLINK_DIR}' \
        -V 'SYSROOT=${_CROSS_DESTDIR:U}' -V 'SDK=${OSX_SDK_PATH:U}' \
        -V 'OPSYS=${OPSYS}' \
        -V 'INTL_ARG=${CMAKE_CONFIGURE_ARGS:M-DLibIntl_INCLUDE_DIR=*}' \
        > "$result/metadata.log"
    meta=$result/metadata.log
    [ -z "$(field FAIL "$meta")" ] || fail "$variant metadata rejected"
    [ "$(field BUILTIN "$meta")" = "$builtin" ] || fail "$variant provider unavailable"
    arg=$(field INTL_ARG "$meta")
    case "$arg" in -DLibIntl_INCLUDE_DIR=*) include=${arg#*=} ;; *) fail 'LibIntl argument missing' ;; esac
    sysroot=$(field SYSROOT "$meta")
    prefix=$(field PREFIX "$meta")
    links=$(field LINKS "$meta")
    # Run only the actual gettext buildlink targets. Do not install packages,
    # run dependency builds, or copy headers to imitate an installed provider.
    "$BMAKE" -C "$pkgsrc/inputmethod/fcitx5" -f "$recipe/Makefile" \
        MAKECONF="$conf" USE_CROSS_COMPILE="$mode" PREFER.gettext="$prefer" \
        WRKDIR="$result/work" _PKGSRC_BARRIER=yes \
        buildlink-directories buildlink-gettext > "$result/buildlink.log" 2>&1
    if [ "$builtin" = yes ]; then
        [ "$include" = "$sysroot$prefix/include" ] || fail 'base include path changed'
        [ ! -e "$links/include/libintl.h" ] || fail 'base buildlink assumption changed'
        package=OFF
    else
        [ -L "$links/include/libintl.h" ] || fail 'actual package header link missing'
        [ "$(readlink "$links/include/libintl.h")" = "$sysroot$prefix/include/gettext/libintl.h" ] || fail 'package header link points to another provider'
        package=ON
    fi
    set -- -S "$out/fixture" -B "$result/cmake" -G Ninja \
        "-DCMAKE_MAKE_PROGRAM=$NINJA" "-DCMAKE_C_COMPILER=$cc" \
        -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
        -DCMAKE_FIND_USE_CMAKE_SYSTEM_PATH=OFF \
        -DCMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH=OFF \
        "-DCMAKE_LIBRARY_PATH=$sysroot$prefix/lib" \
        "-DEXPECT_PACKAGE_GETTEXT=$package" "$arg"
    if [ "$mode" = yes ]; then
        set -- "$@" "-DCMAKE_SYSTEM_NAME=$(field OPSYS "$meta")" \
            "-DCMAKE_SYSROOT=$sysroot" "-DCMAKE_FIND_ROOT_PATH=$sysroot" \
            -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY \
            -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY
    else
        set -- "$@" "-DCMAKE_AR=$NATIVE_AR"
        if [ -n "$(field SDK "$meta")" ]; then
            set -- "$@" "-DCMAKE_OSX_SYSROOT=$(field SDK "$meta")"
        fi
    fi
    "$CMAKE" "$@" > "$result/configure.log" 2>&1 || fail "$variant imported target configure (see $result/configure.log)"
    [ "$(field include "$result/cmake/imported-target.txt")" = "$include" ] || fail 'CMake changed the selected include path'
    "$CMAKE" --build "$result/cmake" --parallel 1 > "$result/consumer.log" 2>&1 || fail "$variant header consumer (see $result/consumer.log)"
    printf 'PASS: %s metadata, actual buildlink, upstream FindLibIntl and header consumer\n' "$variant"
done
echo 'No package was installed and no target program was executed.'
