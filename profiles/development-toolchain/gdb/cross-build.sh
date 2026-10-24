#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), current native GDB built on another host.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 GDB_ARCHIVE GCC16_PREFIX SYSROOT NEW_WORK" >&2; exit 2; }
archive=$1 compiler=$2 sysroot=$3 work=$4
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
recipe=$here/../../../pkgsrc/devel/gdb
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2 ;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use paths without shell metacharacters.' >&2; exit 2 ;; esac
done
jobs=${JOBS:-4}
case "$jobs" in ''|*[!0-9]*|0) echo 'JOBS must be positive.' >&2; exit 2 ;; esac
[ ! -e "$work" ] && [ ! -L "$work" ]
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = \
    cd9fc3fe2b47743840e42c1592d3d87f8302eb18639c0b8b4ba0898002e2348f ]
cross=$compiler/bin/aarch64--netbsd
[ "$("$cross-gcc" -dumpfullversion)" = 16.2.0 ]
[ "$("$cross-gcc" -dumpmachine)" = aarch64--netbsd ]
for name in g++ ar ranlib strip readelf; do [ -x "$cross-$name" ]; done
for library in libgmp.so libmpfr.so libexpat.so libreadline.so libzstd.so; do
    [ -e "$sysroot/usr/pkg/lib/$library" ]
done
[ -e "$sysroot/usr/pkg/gcc16/lib/libstdc++.so.7" ]
[ -f "$sysroot/usr/include/sys/ptrace.h" ]
[ -f "$sysroot/usr/pkg/lib/pkgconfig/libzstd.pc" ]
# pkg-config runs on the build host, but reads only target metadata.
export PKG_CONFIG=${PKG_CONFIG:-pkg-config}
command -v "$PKG_CONFIG" >/dev/null
export PKG_CONFIG_SYSROOT_DIR=$sysroot
export PKG_CONFIG_LIBDIR=$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/pkg/share/pkgconfig:$sysroot/usr/lib/pkgconfig
export PKG_CONFIG_PATH=
"$PKG_CONFIG" --atleast-version=1.4.0 libzstd
mkdir "$work"
mkdir "$work/source" "$work/build" "$work/stage"
tar -xf "$archive" -C "$work/source" --strip-components=1
# Use the package's canonical patch set, including its shared patch symlinks.
for patch_file in "$recipe"/patches/patch-*; do
    [ -f "$patch_file" ]
    patch -f -N -F 0 -d "$work/source" -p1 < "$patch_file"
done > "$work/patch.log" 2>&1
{
    uname -srm
    "$cross-gcc" --version
    shasum -a 256 "$archive" "$0" "$here/libtool-sysroot.sh" "$recipe"/patches/patch-*
    "$PKG_CONFIG" --version
    "$PKG_CONFIG" --modversion libzstd
    shasum -a 256 "$sysroot/usr/pkg/lib/pkgconfig/libzstd.pc"
    shasum -a 256 "$compiler/libexec/gcc/aarch64--netbsd/16.2.0/cc1plus"
    for library in libgmp.so libmpfr.so libexpat.so libreadline.so libzstd.so; do
        shasum -a 256 "$sysroot/usr/pkg/lib/$library"
    done
} > "$work/inputs.txt"
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
export CC="$cross-gcc --sysroot=$sysroot -B$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/"
export CXX="$cross-g++ --sysroot=$sysroot -B$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/"
export AR=$cross-ar RANLIB=$cross-ranlib STRIP=$cross-strip
. "$here/../../common-build-tools/cross/host-gcc16.sh"
ember_require_host_gcc16 HOST_CC c
ember_require_host_gcc16 HOST_CXX c++
export CC_FOR_BUILD=$HOST_CC CXX_FOR_BUILD=$HOST_CXX
# Upstream's ptrace configure probe uses C's pre-C23 non-prototype semantics.
# C17 keeps that test valid while retaining the current GCC and DWARF5.
export CFLAGS='-O2 -g -std=gnu17' CXXFLAGS='-O2 -g'
export CPPFLAGS="-I$sysroot/usr/pkg/include"
export LDFLAGS="-L$sysroot/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib -L$sysroot/usr/pkg/lib -Wl,-rpath,/usr/pkg/lib"
cd "$work/build"
build=$(sh "$work/source/config.guess")
"$work/source/configure" --build="$build" --host=aarch64--netbsd \
    --target=aarch64--netbsd --prefix=/usr/pkg --disable-binutils \
    --disable-gas --disable-ld --disable-gprof --disable-sim \
    --disable-gdbserver --disable-nls --without-python --without-guile \
    --without-debuginfod --without-intel-pt --without-babeltrace --with-zstd \
    --with-gmp="$sysroot/usr/pkg" --with-mpfr="$sysroot/usr/pkg" \
    --with-libexpat-prefix="$sysroot/usr/pkg" --disable-rpath --with-system-zlib \
    --with-system-readline --with-curses --with-separate-debug-dir=/usr/libdata/debug \
    > "$work/configure.log" 2>&1
"${GMAKE:-gmake}" -j "$jobs" configure-gdb > "$work/build.log" 2>&1
sh "$here/libtool-sysroot.sh" "$work/build/gdb/libtool" "$sysroot"
"${GMAKE:-gmake}" -j "$jobs" all-gdb >> "$work/build.log" 2>&1
"${GMAKE:-gmake}" DESTDIR="$work/stage" install-gdb > "$work/install.log" 2>&1
"$cross-strip" "$work/stage/usr/pkg/bin/gdb"
"$cross-readelf" -h -d "$work/stage/usr/pkg/bin/gdb" > "$work/elf.txt"
grep -q 'AArch64' "$work/elf.txt"
grep -q 'NEEDED.*libzstd[.]so' "$work/elf.txt"
if grep -E '(RPATH|RUNPATH).*(/Users/|/private/|/tmp/)' "$work/elf.txt"; then
    echo 'Host path leaked into target runtime search path.' >&2; exit 1
fi
runtime_path=$(awk '/\(RPATH\)|\(RUNPATH\)/ { sub(/^.*\[/, ""); sub(/\].*$/, ""); print }' "$work/elf.txt")
[ "$runtime_path" = /usr/pkg/gcc16/lib:/usr/pkg/lib ] || {
    echo "Unexpected runtime path: $runtime_path" >&2; exit 1;
}
shasum -a 256 "$work/stage/usr/pkg/bin/gdb" > "$work/outputs.sha256"
echo 'GDB 18.1 staged; run native acceptance before installation.'
