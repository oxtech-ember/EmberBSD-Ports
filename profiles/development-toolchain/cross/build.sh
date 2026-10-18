#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted host cross-compiler recipe using Ports sources.
set -eu
usage() {
    echo 'Usage: build.sh [--target aarch64|amd64] EXPORTED_PKGSRC GCC_ARCHIVE SYSROOT NETBSD_TOOLDIR [HOST_MATH_PREFIX] NEW_WORK' >&2
    echo '       build.sh [--target aarch64|amd64] --kernel EXPORTED_PKGSRC GCC_ARCHIVE NETBSD_TOOLDIR [HOST_MATH_PREFIX] NEW_WORK' >&2
    exit 2
}
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
kernel_allowed=yes
. "$profile/cross/target-options.sh"
if [ "$mode" = kernel ]; then
    [ "$#" -eq 4 ] || [ "$#" -eq 5 ] || usage
else
    [ "$#" -eq 5 ] || [ "$#" -eq 6 ] || usage
fi
recipe=$1/lang/gcc16
archive=$2
if [ "$mode" = kernel ]; then
    sysroot=
    tools=$3
    if [ "$#" -eq 5 ]; then
        math=$4 work=$5
    else
        math=${EMBER_HOST_MATH_PREFIX:-} work=$4
    fi
else
    sysroot=$3 tools=$4
    if [ "$#" -eq 6 ]; then
        math=$5 work=$6
    else
        math=${EMBER_HOST_MATH_PREFIX:-} work=$5
    fi
fi
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use paths without whitespace or shell metacharacters.' >&2; exit 2;; esac
done
host_cc=${HOST_CC:-gcc-16}
host_cxx=${HOST_CXX:-g++-16}
if [ "${CROSS_JOBS+x}" = x ]; then
    jobs=$CROSS_JOBS
else
    jobs=$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null) || {
        echo 'Cannot detect host CPU count; set CROSS_JOBS explicitly.' >&2; exit 2;
    }
fi
case "$jobs" in ''|*[!0-9]*) jobs=0;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'CROSS_JOBS must be positive.' >&2; exit 2; }
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'NEW_WORK already exists.' >&2; exit 2; }
if [ "$mode" = applications ]; then
    [ -f "$sysroot/usr/include/stddef.h" ] || { echo 'Target headers missing.' >&2; exit 2; }
    [ -f "$sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0/crtbegin.o" ] || {
        echo 'The sysroot must contain the selected target GCC16 package.' >&2; exit 2;
    }
    [ -d "$sysroot/usr/pkg/gcc16/include/c++/$triplet" ] || {
        echo 'Selected target GCC16 C++ headers missing.' >&2; exit 2;
    }
fi
[ -x "$tools/bin/nbgmake" ] || { echo 'Bootstrap GNU make missing.' >&2; exit 2; }
check_math() {
    case "$math" in /*) ;; *) echo 'Absolute host math prefix required.' >&2; exit 2;; esac
    case "$math" in *[!A-Za-z0-9_./-]*) echo 'Use a simple host math prefix.' >&2; exit 2;; esac
    for library in gmp mpfr mpc; do
        [ -f "$math/lib/lib$library.a" ] || { echo "Host lib$library.a missing." >&2; exit 2; }
    done
    for pair in '__GNU_MP_VERSION:6' '__GNU_MP_VERSION_MINOR:3' '__GNU_MP_VERSION_PATCHLEVEL:0'; do
        macro=${pair%:*}; version=${pair#*:}
        actual=$(awk -v macro="$macro" '$1 == "#define" && $2 == macro {print $3}' "$math/include/gmp.h")
        [ "$actual" = "$version" ] || { echo 'Host GMP 6.3.0 is required; use host-math.sh.' >&2; exit 2; }
    done
    for item in mpfr:MPFR:4:2:2 mpc:MPC:1:4:1; do
        header=${item%%:*}; rest=${item#*:}; macro_prefix=${rest%%:*}; rest=${rest#*:}
        major=${rest%%:*}; rest=${rest#*:}; minor=${rest%%:*}; patchlevel=${rest#*:}
        for pair in "MAJOR:$major" "MINOR:$minor" "PATCHLEVEL:$patchlevel"; do
            macro=${macro_prefix}_VERSION_${pair%:*}; version=${pair#*:}
            actual=$(awk -v macro="$macro" '$1 == "#define" && $2 == macro {print $3}' "$math/include/$header.h")
            [ "$actual" = "$version" ] || { echo "Host $header version mismatch; use host-math.sh." >&2; exit 2; }
        done
    done
}
[ -z "$math" ] || check_math
expected=$(awk -F '\t' '$1 == "gcc" && $2 == "16.2.0" {print $4}' "$profile/sources.tsv")
[ -n "$expected" ] && [ "$(shasum -a 256 "$archive" | awk '{print $1}')" = "$expected" ] || {
    echo 'GCC archive SHA256 mismatch.' >&2; exit 1;
}
# Verify every recorded source patch, including the native-only patch excluded below.
# The common profile disables Graphite and does not extract or patch ISL.
patches=$(awk '/^SHA1 \(patch-/ && $2 != "(patch-isl_configure)" { gsub(/[()]/, "", $2); print $2 }' "$recipe/distinfo")
[ -n "$patches" ] || { echo 'No recipe patches.' >&2; exit 1; }
for name in $patches; do
    case "$name" in patch-*[!A-Za-z0-9_.+-]*|*/*) echo 'Invalid patch name.' >&2; exit 1;; esac
    [ -f "$recipe/patches/$name" ] || { echo "Missing patch: $name" >&2; exit 1; }
    recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name {print $4}' "$recipe/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$recipe/patches/$name" | shasum -a 1 | awk '{print $1}')
    [ "$actual" = "$recorded" ] || { echo "Patch SHA1 mismatch: $name" >&2; exit 1; }
done
# This recipe requires the same repaired frontend as the native nb1 package.
printf '%s\n' "$patches" | grep -qx patch-gcc_cp_module.cc || {
    echo 'GCC16 modules repair missing.' >&2; exit 1;
}
for compiler in "$host_cc" "$host_cxx"; do
    command -v "$compiler" >/dev/null 2>&1 || {
        echo "Host GCC16 compiler missing: $compiler" >&2; exit 2;
    }
    version=$("$compiler" -dumpfullversion) || {
        echo "Cannot identify host GCC16 compiler: $compiler" >&2; exit 2;
    }
    case "$version" in 16.*) ;; *) echo "GCC 16 host compiler required: $compiler ($version)" >&2; exit 2;; esac
done
mkdir -p "$work"
work=$(CDPATH= cd -- "$work" && pwd -P)
if [ -z "$math" ]; then
    HOST_CC=$host_cc HOST_CXX=$host_cxx \
        sh "$profile/cross/host-math.sh" "${EMBER_HOST_MATH_ARCHIVES:-$work/host-archives}" \
        "$tools" "$work/host-math"
    math=$work/host-math/prefix
    check_math
fi
prefix=$work/toolchain
mkdir "$work/src" "$work/build" "$prefix" "$prefix/bin"
GMAKE="$tools/bin/nbgmake" sh "$profile/cross/build-binutils.sh" \
    --target "$target" "$work/binutils"
binutils=$work/binutils/prefix
mkdir -p "$prefix/$triplet/bin" "$prefix/$triplet/lib"
for tool in ar as elfedit ld nm objcopy objdump ranlib readelf size strings strip; do
    [ -x "$binutils/bin/$triplet-$tool" ] || {
        echo "Ports Binutils 2.47 tool missing: $tool" >&2; exit 1;
    }
    cp "$binutils/bin/$triplet-$tool" "$prefix/bin/"
    # GCC's target-tool search path uses objcopy for split DWARF.
    ln -s "../../bin/$triplet-$tool" "$prefix/$triplet/bin/$tool"
done
cp -R "$binutils/$triplet/lib/ldscripts" "$prefix/$triplet/lib/"
shasum -a 256 "$binutils/$triplet/lib/ldscripts/"* > "$work/linker-scripts.sha256"
{
    uname -srm
    printf 'mode=%s\ntarget=%s\ntriplet=%s\nhost_cc=%s\nhost_cxx=%s\n' "$mode" "$target" "$triplet" "$host_cc" "$host_cxx"
    printf 'host_cppflags=%s\nhost_ldflags=%s\n' "${HOST_CPPFLAGS:-}" "${HOST_LDFLAGS:-}"
    "$host_cc" --version
    "$host_cc" -dumpmachine
    "$host_cxx" --version
    shasum -a 256 "$archive" "$recipe/distinfo" "$recipe"/patches/patch-*
    "$tools/bin/nbgmake" --version
    "$prefix/bin/$triplet-ld" --version
    printf 'sysroot=%s\nbootstrap_make=%s\nhost_math=%s\njobs=%s\n' "$sysroot" "$tools" "$math" "$jobs"
    shasum -a 256 "$math/lib/libgmp.a" "$math/lib/libmpfr.a" "$math/lib/libmpc.a"
    cat "$work/binutils/inputs.txt"
} > "$work/inputs.txt"
"$host_cc" -O2 -I"$math/include" "$profile/cross/tests/host-gmp.c" \
    "$math/lib/libgmp.a" -o "$work/host-gmp"
"$work/host-gmp" > "$work/host-gmp.log"
"$work/host-gmp" timer >> "$work/host-gmp.log"
tar -xf "$archive" --strip-components=1 -C "$work/src"
for name in $patches; do
    # pkgsrc's native driver embeds its own install prefix as the target RPATH.
    # A cross compiler's host prefix must never enter target link inputs/RPATHs.
    [ "$name" != patch-gcc_Makefile.in ] || continue
    patch -f -N -F 0 -p0 -d "$work/src" < "$recipe/patches/$name"
done > "$work/patch.log" 2>&1
cd "$work/build"
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
if [ "$mode" = kernel ]; then
    set -- --without-headers --disable-shared --disable-threads
else
    set -- --with-sysroot="$sysroot" --with-gxx-include-dir="$sysroot/usr/pkg/gcc16/include/c++"
fi
# Recursive host libraries and generators also need the selected SDK flags.
CPPFLAGS=${HOST_CPPFLAGS:-}
export CPPFLAGS
# Some host subprojects, including libcody, omit CPPFLAGS in compile rules.
CC=$host_cc CXX=$host_cxx \
    CFLAGS="-O2 ${HOST_CPPFLAGS:-}" CXXFLAGS="-O2 ${HOST_CPPFLAGS:-}" \
    LDFLAGS=${HOST_LDFLAGS:-} \
    ../src/configure --target="$triplet" --prefix="$prefix" \
    "$@" \
    --with-gmp="$math" --with-mpfr="$math" --with-mpc="$math" \
    --with-as="$prefix/bin/$triplet-as" --with-ld="$prefix/bin/$triplet-ld" \
    --enable-languages=c,c++ --disable-bootstrap --disable-multilib \
    --disable-nls --without-isl > "$work/configure.log" 2>&1
"$tools/bin/nbgmake" -j"$jobs" all-gcc > "$work/build.log" 2>&1
"$tools/bin/nbgmake" install-gcc > "$work/install.log" 2>&1
for compiler in gcc g++; do
    [ "$("$prefix/bin/$triplet-$compiler" -dumpfullversion)" = 16.2.0 ]
    [ "$("$prefix/bin/$triplet-$compiler" -dumpmachine)" = "$triplet" ]
done
sh "$profile/cross/tests/split-dwarf.sh" --target "$target" "$prefix" "$work/split-dwarf"
if [ "$target" = aarch64 ]; then
    sh "$profile/cross/tests/lto-binutils.sh" "$prefix" "$work/lto-binutils"
    cat "$work/lto-binutils/inputs.txt" >> "$work/inputs.txt"
fi
echo "GCC16 cross compiler built: $prefix"
if [ "$mode" = kernel ]; then
    echo 'Kernel frontends only; validate the selected fork kernel build and boot separately.'
else
    echo 'Compile the acceptance programs, then run them on EmberBSD before accepting the toolchain.'
fi
