#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the actual selected cross compiler.
# WebKit's own ATOMIC_TEST_SOURCE must link for the target either inline
# (ATOMICS_ARE_BUILTIN) or with -latomic resolved by compiler-rt's
# clang_rt.atomic, the only atomic runtime; never GCC's libatomic.
set -eu
LC_ALL=C
export LC_ALL
[ "$#" -ge 5 ] || { echo 'Usage: check-atomic.sh SYSROOT TRIPLET READELF WEBKIT_COMPILER_FLAGS_CMAKE CXX [FLAGS...]' >&2; exit 2; }
sysroot=$1
triplet=$2
readelf=$3
cmake=$4
shift 4
case "$sysroot:$readelf:$cmake:$1" in /*:/*:/*:/*) ;; *) echo 'Absolute tool and sysroot paths are required' >&2; exit 2 ;; esac
case "$triplet" in
    aarch64--netbsd) machine=AArch64 ;;
    x86_64--netbsd) machine='Advanced Micro Devices X86-64' ;;
    *) echo 'Unsupported WebKit cross triplet' >&2; exit 2 ;;
esac
case "$("$@" -dumpmachine)" in
    "$triplet"|"${triplet%%-*}-unknown-netbsd"*) ;;
    *) echo 'Compiler target mismatch' >&2; exit 1 ;;
esac
work=$(mktemp -d "${TMPDIR:-/tmp}/webkit-atomic.XXXXXX")
trap 'rm -rf "$work"' EXIT
awk '/set\(ATOMIC_TEST_SOURCE \[=\[/ { f = 1; next } /\]=\]\)/ { f = 0 } f' \
    "$cmake" > "$work/t.cpp"
grep -q 'compare_and_swap_pair_weak' "$work/t.cpp" || { echo 'WebKit atomic test source not found' >&2; exit 1; }
mode=inline
if ! "$@" --std=c++17 "$work/t.cpp" -o "$work/t" 2> "$work/inline.log" ||
    "$readelf" -s --dyn-syms "$work/t" | grep -qE 'UND.* __atomic_'; then
    mode=libatomic
    "$@" --std=c++17 "$work/t.cpp" -latomic -o "$work/t"
fi
header=$("$readelf" -h "$work/t")
[ "$(printf '%s\n' "$header" | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')" = "$machine" ]
needed=$("$readelf" -d "$work/t" | sed -n 's/.*(NEEDED).*\[\(.*\)\].*/\1/p')
if printf '%s\n' "$needed" | grep -E '^(libatomic\.so\.|libgcc_s)'; then
    echo 'WebKit atomics resolve to the GCC runtime' >&2; exit 1
fi
if [ "$mode" = libatomic ]; then
    printf '%s\n' "$needed" | grep -q '^libclang_rt\.atomic-' || {
        echo 'WebKit atomics need -latomic but it is not compiler-rt' >&2; exit 1; }
fi
echo "WebKit atomics for $triplet: $mode"
