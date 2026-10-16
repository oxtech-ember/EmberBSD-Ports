#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native Clang defaults from a target sysroot.
set -eu
[ "$#" = 5 ] || {
    echo "Usage: $0 CROSS_GCC TARGET_LLVM_CONFIG SYSROOT GCC_PREFIX NEW_OUTPUT" >&2
    exit 2
}
gcc=$1 llvm=$2 sysroot=$3 target_prefix=$4 output=$5
fail() { echo "Invalid cross GCC metadata: $*" >&2; exit 1; }
for path do
    case "$path" in /*) ;; *) fail 'absolute paths required' ;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) fail 'unsafe path' ;; esac
done
[ -x "$gcc" ] && [ -x "$llvm" ] || fail 'missing build-host query tool'
[ ! -e "$output" ] && [ ! -L "$output" ] || fail 'output exists'
sysroot=$(realpath "$sysroot")
prefix=$(realpath "$sysroot$target_prefix")
[ "$prefix" = "$sysroot$target_prefix" ] || fail 'GCC prefix escapes sysroot'
[ -f "$prefix/bin/gcc" ] || fail 'missing installed target GCC'
[ "$("$gcc" -dumpfullversion)" = 16.2.0 ] || fail 'expected GCC 16.2.0'
[ "$("$llvm" --version)" = 23.1.3 ] || fail 'expected LLVM 23.1.3'
gcc_target=$("$gcc" -dumpmachine)
triple=$("$llvm" --host-target)
# GCC's empty vendor is LLVM's "unknown" vendor; OS version suffixes do
# not change the selected native ABI. Both tools must describe the same CPU.
case "$gcc_target" in aarch64--netbsd*|x86_64--netbsd*) ;; *) fail 'unsupported GCC target' ;; esac
case "$triple" in aarch64-unknown-netbsd*|x86_64-unknown-netbsd*) ;; *) fail 'unsupported LLVM target' ;; esac
case "$gcc_target:$triple" in *[!a-zA-Z0-9_.:+-]*) fail 'unsafe target' ;; esac
normalize() { printf '%s\n' "$1" | sed -e 's/--/-unknown-/' -e 's/netbsd[0-9.]*/netbsd/'; }
[ "$(normalize "$gcc_target")" = "$(normalize "$triple")" ] || fail 'target ABI mismatch'
private=$prefix/lib/gcc/$gcc_target/16.2.0
runtime=$prefix/lib
[ -d "$private" ] && [ -d "$runtime" ] || fail 'missing selected GCC runtime'
query() { "$gcc" --sysroot="$sysroot" -B"$private/" -B"$runtime/" "$@"; }
for name in crtbegin.o crtbeginS.o crtend.o crtendS.o libgcc.a libgcc_s.so.1 libstdc++.so; do
    path=$(query -print-file-name="$name")
    [ -f "$path" ] || fail "missing $name"
    path=$(realpath "$path")
    case "$name" in crt*.o|libgcc.a) directory=$private ;; *) directory=$runtime ;; esac
    [ "${path%/*}" = "$directory" ] || fail "$name outside selected GCC directory"
done
includes=$(query -E -x c++ -v /dev/null 2>&1) || fail 'C++ search probe failed'
includes=$(printf '%s\n' "$includes" | awk '
    /#include <...> search starts here:/ { active=1; next }
    /End of search list/ { active=0 }
    active { sub(/^ +/, ""); if ($0 ~ /\/c\+\+($|\/)/) print }
')
count=0 seen=
for directory in $includes; do
    case "$directory" in *[!a-zA-Z0-9_./+-]*) fail 'unsafe include directory' ;; esac
    [ -d "$directory" ] || fail 'missing C++ include directory'
    directory=$(realpath "$directory")
    case "$directory" in "$prefix"/*) ;; *) fail 'C++ headers outside selected GCC' ;; esac
    case " $seen " in *" $directory "*) fail 'duplicate C++ include directory' ;; esac
    seen="$seen $directory"
    count=$((count + 1))
done
[ "$count" = 3 ] || fail 'expected version, target and backward C++ directories'
mkdir "$output"
{
    echo '# Native common GCC16 defaults; same-triple SDKs use --no-default-config.'
    echo '-stdlib=libstdc++'
    for directory in $seen; do printf '%s\n' "-stdlib++-isystem${directory#"$sysroot"}"; done
    printf '%s\n' "-B${private#"$sysroot"}/"
    printf '%s\n' "-L${private#"$sysroot"}" "-L${runtime#"$sysroot"}" "\$-Wl,-rpath,${runtime#"$sysroot"}"
} > "$output/$triple.cfg"
printf 'etc/clang/%s.cfg\n' "$triple" > "$output/PLIST"
printf '%s\n' "$triple.cfg" > "$output/name"
