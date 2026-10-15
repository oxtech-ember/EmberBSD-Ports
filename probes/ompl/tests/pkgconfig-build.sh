#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross-link a consumer through installed metadata.
set -eu
[ "$#" = 4 ] || {
    echo 'Usage: pkgconfig-build.sh GCC_PREFIX SYSROOT STAGED_PREFIX NEW_OUTPUT' >&2; exit 2;
}
compiler=$1 sysroot=$2 prefix=$3 out=$4
for path do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple absolute paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
tests=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cxx=$compiler/bin/aarch64--netbsd-g++
[ "$("$cxx" -dumpfullversion)" = 16.2.0 ]
[ "$("$cxx" -dumpmachine)" = aarch64--netbsd ]
"$tests/pkgconfig-contract.sh" "$prefix" "$sysroot"
PKG_CONFIG_PATH=
PKG_CONFIG_LIBDIR=$prefix/lib/pkgconfig:$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/pkg/share/pkgconfig
PKG_CONFIG_SYSROOT_DIR=$sysroot
export PKG_CONFIG_PATH PKG_CONFIG_LIBDIR PKG_CONFIG_SYSROOT_DIR
pkg_config=${PKG_CONFIG:-pkg-config}
cflags=$("$pkg_config" --cflags ompl)
libs=$("$pkg_config" --libs ompl)
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
headers=$sysroot/usr/pkg/gcc16/include/c++
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
mkdir -p "$out"
sha256sum "$prefix/lib/pkgconfig/ompl.pc" "$tests/pkgconfig-consumer.cc" "$0" > "$out/inputs.sha256"
# Split only trusted pkg-config option lists. All input paths use the simple
# alphabet checked above. Stage overrides locate OMPL before final sysroot merge.
# Do not add a Boost library flag here: the installed .pc must provide it.
set -- "$cxx" --sysroot="$sysroot" -B"$crt/" -L"$runtime" \
    -isystem "$headers" -isystem "$headers/aarch64--netbsd" -isystem "$headers/backward" \
    -I"$prefix/include/ompl-2.0" $cflags -O2 -Wall -Wextra -Wpedantic \
    "$tests/pkgconfig-consumer.cc" -L"$prefix/lib" $libs \
    -Wl,--no-copy-dt-needed-entries -Wl,-rpath-link,"$sysroot/usr/pkg/lib" \
    -Wl,-rpath,/usr/pkg/lib:/usr/pkg/gcc16/lib -o "$out/ompl-pkgconfig-contract"
printf '%s\n' "$@" > "$out/compiler-arguments.txt"
pwd -P > "$out/compiler-directory.txt"
"$@"
"$compiler/bin/aarch64--netbsd-readelf" -h -d "$out/ompl-pkgconfig-contract" > "$out/elf.txt"
grep 'Machine:.*AArch64' "$out/elf.txt" > /dev/null
echo "Installed pkg-config consumer cross-link: PASS ($out/ompl-pkgconfig-contract)"
