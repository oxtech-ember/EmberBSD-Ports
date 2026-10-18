#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
set -eu
umask 022
[ "$#" = 3 ] || { echo 'Usage: build.sh native-bootstrap|target ABS_SOURCE ABS_NEW_WORK' >&2; exit 2; }
mode=$1
source=$2
work=$3
case "$mode" in native-bootstrap|target) ;; *) exit 2 ;; esac
for path in "$source" "$work"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
done
[ -f "$source/.ember-source-pin" ] || { echo 'Use prepare-source.sh first.' >&2; exit 2; }
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Build path already exists.' >&2; exit 2; }
: "${CC:?Set the C compiler}"
: "${CXX:?Set the C++ compiler}"
: "${PREFIX:?Set the installation prefix}"
case "$PREFIX" in /*) ;; *) exit 2 ;; esac
jobs=${JOBS:-2}
case "$jobs" in ''|0|*[!0-9]*) exit 2 ;; esac
make=${MAKE:-make}
build_triplet=$(sh "$source/config.guess")
if [ "$mode" = target ]; then
    unset LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH
    : "${EMBERBSD_SYSROOT:?Set the verified EmberBSD sysroot}"
    : "${EMBERBSD_GCC_RUNTIME:?Set the common GCC16 runtime prefix}"
    : "${CC_FOR_BUILD:?Set the native generator compiler}"
    : "${TARGET_LIBTOOL:?Set the common configured target Libtool script}"
    [ "$PREFIX" = /usr/pkg ] || { echo 'Target prefix must be /usr/pkg.' >&2; exit 2; }
    for compiler in "$CC" "$CXX"; do
        [ "$("$compiler" -dumpfullversion)" = 16.2.0 ] || { echo 'Target requires GCC 16.2.0.' >&2; exit 2; }
        [ "$("$compiler" -dumpmachine)" = aarch64--netbsd ] || { echo 'Unexpected target triplet.' >&2; exit 2; }
    done
    [ -f "$EMBERBSD_SYSROOT/usr/include/stdio.h" ] && [ -f "$EMBERBSD_SYSROOT/usr/lib/libc.so" ]
    [ -f "$TARGET_LIBTOOL" ]
    host_triplet=aarch64--netbsd
else
    host_triplet=$build_triplet
    CC_FOR_BUILD=$CC
    export CC_FOR_BUILD
fi
mkdir "$work"
mkdir "$work/logs" "$work/cli" "$work/shared" "$work/stage"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
{
    printf 'Mode: %s\nPrefix: %s\n' "$mode" "$PREFIX"
    "$CC" --version
    "$CXX" --version
    "$CC" -dumpmachine
    "$make" --version
    cat "$source/.ember-source-pin"
} > "$work/logs/inputs.txt"
(cd "$source" && autoconf && autoheader) > "$work/logs/autoconf.log" 2>&1
export CC CXX
CFLAGS=${CFLAGS:--O2 -g -fPIC}
CXXFLAGS=${CXXFLAGS:--O2 -g -fPIC}
if [ "$mode" = target ]; then
    for path in "$EMBERBSD_SYSROOT" "$EMBERBSD_GCC_RUNTIME"; do
        case "$path" in /*) ;; *) exit 2 ;; esac
        case "$path" in *[!a-zA-Z0-9_./-]*) exit 2 ;; esac
    done
    [ -f "$EMBERBSD_GCC_RUNTIME/include/c++/vector" ]
    [ -f "$EMBERBSD_GCC_RUNTIME/lib/libstdc++.so" ]
    common="--sysroot=$EMBERBSD_SYSROOT -B$EMBERBSD_GCC_RUNTIME/lib/gcc/aarch64--netbsd/16.2.0/ -B$EMBERBSD_GCC_RUNTIME/lib/"
    CFLAGS="$CFLAGS $common"
    CXXFLAGS="$CXXFLAGS $common -isystem $EMBERBSD_GCC_RUNTIME/include/c++ -isystem $EMBERBSD_GCC_RUNTIME/include/c++/aarch64--netbsd -isystem $EMBERBSD_GCC_RUNTIME/include/c++/backward"
    LDFLAGS="${LDFLAGS:-} -L$EMBERBSD_GCC_RUNTIME/lib -Wl,-rpath-link,$EMBERBSD_GCC_RUNTIME/lib -Wl,-rpath,/usr/pkg/gcc16/lib:/usr/pkg/lib"
    export LDFLAGS
fi
export CFLAGS CXXFLAGS
# Install the CLI last. Both interfaces install the same XSPICE model names;
# one CLI-built model set serves both consumers in the composite package.
for interface in shared cli; do
    (
        cd "$work/$interface"
        if [ "$interface" = shared ]; then
            set -- --with-ngshared=yes
        else
            set -- --with-ngshared=no --with-readline=yes --with-editline=no --without-x
        fi
        "$source/configure" --prefix="$PREFIX" --libdir="$PREFIX/lib" \
            --build="$build_triplet" --host="$host_triplet" \
            --enable-cider --enable-openmp --with-fftw3=yes \
            --enable-shared --disable-static --disable-maintainer-mode \
            --disable-silent-rules "$@" > "$work/logs/$interface-configure.log" 2>&1
        for feature in CIDER XSPICE KLU OSDI USE_OMP HAVE_LIBFFTW3; do
            grep "^#define $feature " src/include/ngspice/config.h >/dev/null || {
                echo "Missing selected feature: $feature" >&2; exit 1;
            }
        done
        if [ "$interface" = cli ]; then
            grep '^#define HAVE_GNUREADLINE ' src/include/ngspice/config.h >/dev/null
        fi
        set --
        if [ "$mode" = target ]; then set -- "LIBTOOL=sh $TARGET_LIBTOOL"; fi
        "$make" -j "$jobs" "$@" > "$work/logs/$interface-build.log" 2>&1
        "$make" "$@" DESTDIR="$work/stage" install > "$work/logs/$interface-install.log" 2>&1
    )
done
"$CC" ${CPPFLAGS:-} $CFLAGS -I"$work/stage$PREFIX/include" \
    "$here/tests/api-contract.c" ${LDFLAGS:-} -L"$work/stage$PREFIX/lib" \
    -lngspice -lm -o "$work/api-contract"
mkdir -p "$work/stage$PREFIX/share/licenses/ngspice"
cp "$source/COPYING" "$work/stage$PREFIX/share/licenses/ngspice/COPYING"
printf 'Built %s; stage %s. Runtime checks remain separate.\n' "$mode" "$work/stage"
