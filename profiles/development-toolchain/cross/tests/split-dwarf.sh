#!/bin/sh
# Origin: EmberBSD (AI-assisted), exercise GCC's installed target objcopy lookup.
set -eu
usage() { echo "Usage: $0 [--target aarch64|amd64] CROSS_PREFIX NEW_WORK" >&2; exit 2; }
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
. "$here/target-options.sh"
[ "$#" = 2 ] || usage
prefix=$1 work=$2
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Output already exists.' >&2; exit 2; }
mkdir "$work"
printf 'struct split_record { long value; }; struct split_record split_data;\n' > "$work/test.c"
# No -B, COMPILER_PATH or host GNU binutils in PATH may hide a broken prefix.
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH
PATH=/usr/bin:/bin
export PATH
"$prefix/bin/$triplet-gcc" -O2 -gdwarf-5 -gsplit-dwarf -c "$work/test.c" -o "$work/test.o"
[ -s "$work/test.dwo" ]
"$prefix/bin/$triplet-readelf" --debug-dump=info "$work/test.o" > "$work/info.txt"
grep -q 'DW_UT_skeleton' "$work/info.txt"
grep -q 'DW_UT_split_compile' "$work/info.txt"
grep -q 'split_record' "$work/info.txt"
echo 'PASS: installed GCC creates and follows split DWARF without tool-path overrides'
