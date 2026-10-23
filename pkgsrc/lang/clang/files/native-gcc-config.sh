#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted native Clang/GCC16 package integration.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 GCC16 CLANG GCC_PREFIX NEW_OUTPUT" >&2; exit 2; }
gcc=$1 clang=$2 prefix=$3 output=$4
fail() { echo "Invalid common GCC metadata: $*" >&2; exit 1; }
case "$gcc:$clang:$prefix:$output" in *[!a-zA-Z0-9_./:+-]*) fail 'unsafe path' ;; esac
[ -x "$gcc" ] && [ -x "$clang" ] || fail 'missing compiler'
[ ! -e "$output" ] && [ ! -L "$output" ] || fail 'output exists'
prefix=$(realpath "$prefix")
[ "$("$gcc" -dumpfullversion)" = 16.2.0 ] || fail 'expected GCC 16.2.0'
gcc_target=$("$gcc" -dumpmachine)
triple=$("$clang" --no-default-config -print-target-triple)
normalized=$("$clang" --no-default-config --target="$gcc_target" -print-target-triple)
case "$triple:$normalized" in *[!a-zA-Z0-9_.:+-]*) fail 'invalid target' ;; esac
case "$triple" in *-netbsd*) ;; *) fail 'native target must be NetBSD' ;; esac
case "$normalized" in *-netbsd*) ;; *) fail 'GCC target must be NetBSD' ;; esac
# NetBSD version suffixes may differ between the installed GCC and LLVM
# config.guess; vendor, architecture and ABI/environment must still agree.
native_abi=$(printf '%s\n' "$triple" | sed 's/netbsd[0-9.]*/netbsd/')
gcc_abi=$(printf '%s\n' "$normalized" | sed 's/netbsd[0-9.]*/netbsd/')
[ "$native_abi" = "$gcc_abi" ] || fail 'native target ABI mismatch'
private=
runtime=
for name in crtbegin.o crtbeginS.o crtend.o crtendS.o libgcc.a libgcc_s.so.1 libstdc++.so; do
    path=$("$gcc" -print-file-name="$name")
    [ -f "$path" ] || fail "missing $name"
    path=$(realpath "$path")
    case "$path" in "$prefix"/*) ;; *) fail "$name outside current prefix" ;; esac
    directory=${path%/*}
    case "$name" in
        crt*.o|libgcc.a)
            [ -z "$private" ] || [ "$private" = "$directory" ] || fail 'ambiguous CRT prefix'
            private=$directory ;;
        libgcc_s.so.1|libstdc++.so)
            [ -z "$runtime" ] || [ "$runtime" = "$directory" ] || fail 'ambiguous shared runtime prefix'
            runtime=$directory ;;
    esac
done
# Ask the selected real compiler; do not guess version/target header directories.
includes=$("$gcc" -E -x c++ -v /dev/null 2>&1) || fail "C++ search probe failed"
includes=$(printf "%s\n" "$includes" | awk '
    /#include <...> search starts here:/ { active=1; next }
    /End of search list/ { active=0 }
    active { sub(/^ +/, ""); if ($0 ~ /\/c\+\+\//) print }
')
count=0
seen=
for directory in $includes; do
    case "$directory" in *[!a-zA-Z0-9_./+-]*) fail 'unsafe include directory' ;; esac
    [ -d "$directory" ] || fail 'missing C++ include directory'
    directory=$(realpath "$directory")
    case "$directory" in "$prefix"/*) ;; *) fail 'C++ headers outside current prefix' ;; esac
    case " $seen " in *" $directory "*) fail 'duplicate C++ include directory' ;; esac
    seen="$seen $directory"
    count=$((count + 1))
done
[ "$count" = 3 ] || fail 'expected version, target and backward C++ directories'
# The metadata names a real package-owned compiler and native target only.
case "$(realpath "$gcc")" in "$prefix"/bin/*) ;; *) fail 'compiler outside current prefix' ;; esac
mkdir "$output"
{
    echo '# Native common GCC16 defaults; same-triple SDKs use --no-default-config.'
    echo '-stdlib=libstdc++'
    for directory in $seen; do printf '%s\n' "-stdlib++-isystem$directory"; done
    printf '%s\n' "-B$private/"
    # Standard -L options are linker-only and precede the driver's /usr/lib.
    # A $-tail -L is not consumed by NetBSD's early addAllArgs; forwarding it
    # through -Wl in the tail would put the base search directory first.
    printf '%s\n' "-L$private" "-L$runtime" "\$-Wl,-rpath,$runtime"
} > "$output/$triple.cfg"
printf 'etc/clang/%s.cfg\n' "$triple" > "$output/PLIST"
printf '%s\n' "$triple.cfg" > "$output/name"
