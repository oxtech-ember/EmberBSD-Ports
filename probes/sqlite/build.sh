#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Build the common SQLite recipe in a fresh output.
set -eu
umask 022
usage() {
    echo 'Usage: build.sh --cross GCC_PREFIX SYSROOT ARCHIVE NEW_OUTPUT' >&2
    echo '       build.sh --native PREFIX ARCHIVE NEW_OUTPUT' >&2
    exit 2
}
mode=${1:-}
[ "$#" -gt 0 ] || usage
shift
case "$mode" in
    --cross) [ "$#" = 4 ] || usage; compiler=$1 sysroot=$2 archive=$3 out=$4; prefix=/usr/pkg ;;
    --native) [ "$#" = 3 ] || usage; prefix=$1 archive=$2 out=$3; compiler= sysroot= ;;
    *) usage ;;
esac
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple absolute paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
jobs=${JOBS:-1}
case "$jobs" in ''|*[!0-9]*) jobs=0;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'JOBS must be positive.' >&2; exit 2; }
probe=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
recipe=$probe/../../profiles/common-build-tools/recipes/databases/sqlite3
expected=$(awk '$1=="sqlite-autoconf-3540100.tar.gz" {print $2}' "$probe/sources.tsv")
[ "${#expected}" = 64 ]
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
build_cc=$(command -v "${BUILD_CC:-gcc}")
[ "$("$build_cc" -dumpfullversion)" = 16.2.0 ] || { echo 'Native GCC 16.2.0 required for build tools.' >&2; exit 2; }
if [ "$mode" = --cross ]; then
    cc=$compiler/bin/aarch64--netbsd-gcc
    ar=$compiler/bin/aarch64--netbsd-ar
    ranlib=$compiler/bin/aarch64--netbsd-ranlib
    readelf=$compiler/bin/aarch64--netbsd-readelf
    [ "$("$cc" -dumpmachine)" = aarch64--netbsd ]
    # Autosetup requires an explicit canonical vendor field. This configure
    # spelling does not change the compiler triplet or the EmberBSD sysroot.
    host=aarch64-unknown-netbsd
    crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
    [ -f "$crt/crtbeginS.o" ] && [ -f "$sysroot/usr/include/pthread.h" ]
    target_flags="--sysroot=$sysroot -B$crt/ -L$sysroot/usr/pkg/gcc16/lib -march=armv8-a"
else
    cc=$(command -v "${CC:-gcc}")
    ar=$(command -v ar)
    ranlib=$(command -v ranlib)
    readelf=$(command -v readelf)
    host=$("$cc" -dumpmachine)
    target_flags=
fi
[ "$("$cc" -dumpfullversion)" = 16.2.0 ] || { echo 'GCC 16.2.0 required.' >&2; exit 2; }
for tool in make tar cmake ninja; do command -v "$tool" >/dev/null; done
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH
mkdir -p "$out/source" "$out/build" "$out/logs"
tar -xf "$archive" --strip-components=1 -C "$out/source"
(cd "$out/source" && patch -f -p0 -F 0 -i "$recipe/patches/patch-autosetup_proj.tcl")
feature_flags=$(awk '/^SQLITE_CONFIGURE_ARGS=/ {sub(/^[^=]*=[ \t]*/, ""); print}' "$recipe/features.mk")
feature_flags="$feature_flags $(awk '/^SQLITE_ELF_CONFIGURE_ARGS=/ {sub(/^[^=]*=[ \t]*/, ""); print}' "$recipe/features.mk")"
feature_defines=$(awk '/^SQLITE_CPPFLAGS=/ {sub(/^[^=]*=[ \t]*/, ""); print}' "$recipe/features.mk")
[ -n "$feature_flags" ] && [ -n "$feature_defines" ]
{
    uname -srm
    "$cc" --version
    "$cc" -dumpmachine
    "$build_cc" --version
    make --version
    cmake --version
    printf 'mode=%s\nprefix=%s\nsysroot=%s\njobs=%s\nfeatures=%s\ndefines=%s\n' "$mode" "$prefix" "$sysroot" "$jobs" "$feature_flags" "$feature_defines"
    sha256sum "$archive" "$0" "$recipe/features.mk" "$recipe/files/SOURCE" "$recipe/patches/patch-autosetup_proj.tcl"
} > "$out/inputs.txt"
run() {
    name=$1; shift
    status=0
    "$@" > "$out/logs/$name.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$out/logs/$name.status"
    if [ "$status" -ne 0 ]; then tail -60 "$out/logs/$name.log" >&2; exit "$status"; fi
}
cd "$out/build"
# Autosetup's bootstrap Tcl implementation is built with the native compiler.
# The generated SQLite objects, shared library and CLI use the selected target.
run configure env CC="$cc" CC_FOR_BUILD="$build_cc" AR="$ar" RANLIB="$ranlib" \
    CCACHE=none CFLAGS="-O2 -g -std=gnu17 $target_flags" CPPFLAGS="$feature_defines" \
    LDFLAGS="-Wl,-rpath,$prefix/lib" \
    "$out/source/configure" --build="$("$build_cc" -dumpmachine)" --host="$host" \
    --prefix="$prefix" --mandir="$prefix/man" $feature_flags
# The dynamically linked CLI uses make's LDFLAGS directly. Autosetup records
# configure-time LDFLAGS separately for the library, so pass both interfaces.
run build make -j"$jobs" V=1 LDFLAGS="-Wl,-rpath,$prefix/lib"
run install make DESTDIR="$out/stage" install
run licenses sh "$recipe/files/install-licenses.sh" "$out/source" "$out/stage$prefix" "$recipe"
printf '%s\n' "$prefix" > "$out/prefix.txt"
(cd "$out/stage$prefix" && find . \( -type f -o -type l \) | sed 's|^./||' | LC_ALL=C sort) > "$out/PLIST"
if [ -f "$recipe/PLIST" ]; then
    sed '/^@comment/d;/^$/d;s/${PKGVERSION}/3.54.1/g' "$recipe/PLIST" | LC_ALL=C sort > "$out/expected-PLIST"
    cmp "$out/PLIST" "$out/expected-PLIST"
fi
"$readelf" -h -d "$out/stage$prefix/lib/libsqlite3.so.3.54.1" "$out/stage$prefix/bin/sqlite3" > "$out/elf.txt"
grep 'NEEDED.*\[libsqlite3.so.0\]' "$out/elf.txt" >/dev/null
[ "$(grep -E '(RPATH|RUNPATH)' "$out/elf.txt" | grep -F -c "$prefix/lib")" = 2 ] || {
    echo 'The shared library and CLI must retain the selected runtime prefix.' >&2; exit 1;
}
if [ "$mode" = --cross ]; then
    [ "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 2 ]
    for path in "$compiler" "$sysroot" "$out"; do
        if grep -E 'RPATH|RUNPATH|NEEDED' "$out/elf.txt" | grep -F "$path"; then
            echo 'Build-host runtime path leaked.' >&2; exit 1
        fi
    done
fi
echo "Staged SQLite 3.54.1: $out/stage$prefix"
