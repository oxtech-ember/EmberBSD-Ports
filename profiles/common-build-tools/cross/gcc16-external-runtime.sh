#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Layer a cross-built GCC16 compiler stage
# over the installed gcc16-runtime provider in the target sysroot.
set -eu
[ "$#" = 7 ] || {
    echo 'Usage: gcc16-external-runtime.sh DESTDIR PREFIX SYSROOT PKG_DBDIR PKG_INFO READELF TRIPLET' >&2
    exit 2
}
destdir=$1 prefix=$2 sysroot=$3 pkgdb=$4 pkg_info=$5 readelf=$6 triplet=$7
fail() { echo "gcc16-external-runtime: $*" >&2; exit 1; }
for path in "$destdir" "$prefix" "$sysroot" "$pkgdb" "$pkg_info" "$readelf"; do
    case "$path" in /*) ;; *) fail 'absolute paths required' ;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) fail 'unsafe path' ;; esac
done
case "$triplet" in aarch64--netbsd|x86_64--netbsd) ;; *) fail 'unsupported target' ;; esac
[ -x "$pkg_info" ] && [ -x "$readelf" ] || fail 'missing build-host tool'
[ -d "$destdir$prefix/gcc16" ] || fail 'missing compiler stage'
# The compiler headers select the TLS std::call_once ABI of the runtime.
config=$destdir$prefix/gcc16/include/c++/$triplet/bits/c++config.h
[ -f "$config" ] || fail 'missing staged c++config.h'
[ "$(grep -c '^#define _GLIBCXX_HAVE_TLS 1$' "$config" || true)" = 1 ] || \
    fail 'staged C++ headers do not select the TLS runtime ABI'
# Consumers already in the sysroot used the runtime-stage configuration.
# Installing the compiler replaces it; the configuration must not change.
installed_config=$sysroot$prefix/gcc16/include/c++/$triplet/bits/c++config.h
[ -f "$installed_config" ] || fail 'missing sysroot c++config.h'
cmp -s "$installed_config" "$config" || {
    diff "$installed_config" "$config" >&2 || true
    fail 'staged C++ configuration differs from the sysroot runtime stage'
}
dbdir=$sysroot$pkgdb
runtime=$("$pkg_info" -K "$dbdir" -e 'gcc16-runtime>=16.2.0nb6') || fail 'install gcc16-runtime>=16.2.0nb6 in the sysroot first'
[ -n "$runtime" ] && [ "$(printf '%s\n' "$runtime" | wc -l)" -eq 1 ] || fail 'expected one runtime provider'
work=$(mktemp -d "${TMPDIR:-/tmp}/gcc16-external-runtime.XXXXXX")
trap 'rm -rf "$work"' EXIT
"$pkg_info" -K "$dbdir" -qL "$runtime" > "$work/all"
# Licenses keep package-specific names; only the shared runtime is layered.
grep "^$prefix/gcc16/" "$work/all" > "$work/files" || fail 'runtime provider lists no GCC16 files'
abi() {
    "$readelf" -h -W "$1" | awk '$1 == "Type:" { print "type", $2 }'
    "$readelf" -d -W "$1" | awk '$2 == "(SONAME)" || $2 == "(NEEDED)" { print $2, $NF }'
    # Values differ between builds. Object sizes are part of the ABI.
    "$readelf" --dyn-syms -W "$1" | awk '
        $1 ~ /^[0-9]+:$/ && NF >= 8 {
            name = $8; for (i = 9; i <= NF; i++) name = name " " $i
            size = ($4 == "OBJECT" || $4 == "TLS") ? $3 : "-"
            print $4, $5, $6, ($7 == "UND" ? "UND" : "DEF"), size, name
        }' | sort
}
count=0
while IFS= read -r path; do
    case "$path" in *[!a-zA-Z0-9_./+-]*) fail 'unsafe runtime path' ;; esac
    stage=$destdir$path installed=$sysroot$path
    if [ -L "$installed" ]; then
        [ -L "$stage" ] || fail "compiler stage lacks runtime link $path"
        [ "$(readlink "$stage")" = "$(readlink "$installed")" ] || fail "runtime link differs: $path"
    elif [ -f "$installed" ]; then
        [ -f "$stage" ] && [ ! -L "$stage" ] || fail "compiler stage lacks runtime file $path"
        abi "$installed" > "$work/runtime.abi"
        abi "$stage" > "$work/stage.abi"
        grep -qx 'type DYN' "$work/runtime.abi" || fail "runtime file is not a shared object: $path"
        cmp -s "$work/runtime.abi" "$work/stage.abi" || {
            diff "$work/runtime.abi" "$work/stage.abi" >&2 || true
            fail "runtime ABI differs: $path"
        }
    else
        fail "installed runtime file is missing: $path"
    fi
    count=$((count + 1))
done < "$work/files"
while IFS= read -r path; do
    rm -f "$destdir$path"
done < "$work/files"
echo "gcc16-external-runtime: $count files match $runtime and are left to that provider"
