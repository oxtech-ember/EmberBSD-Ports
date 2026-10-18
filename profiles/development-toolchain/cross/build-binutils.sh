#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; build the cross Binutils selected by the GCC16 recipe.
set -eu
usage() {
    echo 'Usage: build-binutils.sh [--target aarch64|amd64] NEW_WORK' >&2
    exit 2
}
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
profile=$(CDPATH= cd -- "$here/.." && pwd -P)
ports=$(CDPATH= cd -- "$profile/../.." && pwd -P)
kernel_allowed=no
. "$here/target-options.sh"
[ "$#" -eq 1 ] || usage
work=$1
case "$work" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
case "$work" in *[!A-Za-z0-9_./-]*) echo 'Use paths without whitespace or shell metacharacters.' >&2; exit 2;; esac
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'NEW_WORK already exists.' >&2; exit 2; }
if [ "${CROSS_JOBS+x}" = x ]; then
    jobs=$CROSS_JOBS
else
    jobs=$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null) || {
        echo 'Cannot detect host CPU count; set CROSS_JOBS explicitly.' >&2; exit 2;
    }
fi
case "$jobs" in ''|*[!0-9]*) jobs=0;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'CROSS_JOBS must be positive.' >&2; exit 2; }
gmake=${GMAKE:-gmake}
host_cc=${HOST_CC:-gcc-16}
host_cxx=${HOST_CXX:-g++-16}
command -v "$gmake" >/dev/null 2>&1 || { echo 'GNU make missing.' >&2; exit 2; }
for compiler in "$host_cc" "$host_cxx"; do
    command -v "$compiler" >/dev/null 2>&1 || {
        echo "Host GCC16 compiler missing: $compiler" >&2; exit 2;
    }
    version=$("$compiler" -dumpfullversion) || {
        echo "Cannot identify host GCC16 compiler: $compiler" >&2; exit 2;
    }
    case "$version" in 16.*) ;; *) echo "GCC 16 host compiler required: $compiler ($version)" >&2; exit 2;; esac
done
recipe=$ports/profiles/common-build-tools/recipes/devel/binutils
manifest=$ports/profiles/common-build-tools/sources.tsv
archive_name=binutils-2.47.tar.xz
expected=$(awk -F '\t' -v name="$archive_name" '$1 == name {print $2}' "$manifest")
url=$(awk -F '\t' -v name="$archive_name" '$1 == name {print $3}' "$manifest")
[ -n "$expected" ] && [ -n "$url" ] || { echo 'Pinned Binutils source is missing.' >&2; exit 1; }
dist_sha512=$(awk '$1 == "SHA512" && $2 == "(binutils-2.47.tar.xz)" {print $4}' "$recipe/distinfo")
dist_size=$(awk '$1 == "Size" && $2 == "(binutils-2.47.tar.xz)" {print $4}' "$recipe/distinfo")
[ -n "$dist_sha512" ] && [ -n "$dist_size" ] || { echo 'Binutils distinfo is incomplete.' >&2; exit 1; }
mkdir "$work"
work=$(CDPATH= cd -- "$work" && pwd -P)
archive=$work/$archive_name
if [ -n "${EMBER_BINUTILS_ARCHIVE:-}" ]; then
    case "$EMBER_BINUTILS_ARCHIVE" in /*) ;; *) echo 'EMBER_BINUTILS_ARCHIVE must be absolute.' >&2; exit 2;; esac
    case "$EMBER_BINUTILS_ARCHIVE" in *[!A-Za-z0-9_./-]*) echo 'Use a simple archive path.' >&2; exit 2;; esac
    [ -f "$EMBER_BINUTILS_ARCHIVE" ] || { echo 'Binutils archive missing.' >&2; exit 1; }
    cp "$EMBER_BINUTILS_ARCHIVE" "$archive"
else
    curl -fL "$url" -o "$archive.part"
    mv "$archive.part" "$archive"
fi
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = "$expected" ] || {
    echo 'Binutils archive SHA256 mismatch.' >&2; exit 1;
}
[ "$(shasum -a 512 "$archive" | awk '{print $1}')" = "$dist_sha512" ] || {
    echo 'Binutils archive SHA512 mismatch.' >&2; exit 1;
}
[ "$(wc -c < "$archive" | tr -d ' ')" = "$dist_size" ] || {
    echo 'Binutils archive size mismatch.' >&2; exit 1;
}
patches=$(awk '/^SHA1 \(patch-/ { gsub(/[()]/, "", $2); print $2 }' "$recipe/distinfo")
[ -n "$patches" ] || { echo 'Binutils recipe has no patches.' >&2; exit 1; }
for name in $patches; do
    case "$name" in patch-*[!A-Za-z0-9_.+-]*|*/*) echo 'Invalid Binutils patch name.' >&2; exit 1;; esac
    [ -f "$recipe/patches/$name" ] || { echo "Missing Binutils patch: $name" >&2; exit 1; }
    recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name {print $4}' "$recipe/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$recipe/patches/$name" | shasum -a 1 | awk '{print $1}')
    [ -n "$recorded" ] && [ "$actual" = "$recorded" ] || {
        echo "Binutils patch SHA1 mismatch: $name" >&2; exit 1;
    }
done
src=$work/src
build=$work/build
prefix=$work/prefix
mkdir "$src" "$build" "$prefix"
tar -xf "$archive" --strip-components=1 -C "$src"
: > "$work/patch.log"
for name in $patches; do
    printf 'patch=%s\n' "$name" >> "$work/patch.log"
    patch -f -N -F 0 -p0 -d "$src" < "$recipe/patches/$name" \
        >> "$work/patch.log" 2>&1 || { cat "$work/patch.log" >&2; exit 1; }
done
if [ "$(uname -s)" = Linux ] || [ "$(uname -s)" = Darwin ]; then
    set -- --disable-libctf
else
    set --
fi
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
(
    cd "$build"
    CC=$host_cc CXX=$host_cxx \
        "$src/configure" --target="$triplet" --prefix="$prefix" \
        --program-prefix="$triplet-" --enable-plugins --disable-nls \
        --disable-gprofng "$@" > "$work/configure.log" 2>&1
    MAKEINFO=true "$gmake" -j"$jobs" > "$work/build.log" 2>&1
    MAKEINFO=true "$gmake" install > "$work/install.log" 2>&1
)
for tool in ar as elfedit ld nm objcopy objdump ranlib readelf size strings strip; do
    [ -x "$prefix/bin/$triplet-$tool" ] || {
        echo "Installed Binutils tool missing: $tool" >&2; exit 1;
    }
done
for tool in as ld readelf; do
    version=$($prefix/bin/$triplet-$tool --version 2>&1 | sed -n '1p')
    case "$version" in *' 2.47'*) ;; *) echo "Unexpected GNU $tool version: $version" >&2; exit 1;; esac
done
[ -d "$prefix/$triplet/lib/ldscripts" ] && \
    [ -n "$(find "$prefix/$triplet/lib/ldscripts" -type f -print | sed -n '1p')" ] || {
    echo 'Installed Binutils linker scripts missing.' >&2; exit 1;
}
{
    uname -srm
    printf 'target=%s\ntriplet=%s\nhost_cc=%s\nhost_cxx=%s\ngmake=%s\njobs=%s\n' \
        "$target" "$triplet" "$host_cc" "$host_cxx" "$gmake" "$jobs"
    printf 'configure=--target=%s --program-prefix=%s- --enable-plugins --disable-nls --disable-gprofng\n' \
        "$triplet" "$triplet"
    "$host_cc" --version
    "$host_cc" -dumpmachine
    "$host_cxx" --version
    "$gmake" --version | sed -n '1p'
    "$prefix/bin/$triplet-as" --version | sed -n '1p'
    "$prefix/bin/$triplet-ld" --version | sed -n '1p'
    shasum -a 256 "$archive" "$recipe/distinfo" "$recipe"/patches/patch-*
} > "$work/inputs.txt"
echo "Binutils 2.47 cross tools built: $prefix"
