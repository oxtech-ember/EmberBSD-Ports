#!/bin/sh
# Native packages link compiler-rt, libunwind and libc++, so no package may
# search or point at the retired GCC 16 prefix: neither its recipe nor,
# when given, its installed ELF files (RUNPATH and NEEDED).
# Usage: no-gcc16-paths.sh RECIPE_DIR... [-- READELF ELF...]
set -eu
[ "$#" -gt 0 ] || { echo 'usage: no-gcc16-paths.sh RECIPE_DIR... [-- READELF ELF...]' >&2; exit 2; }
fail=0
while [ "$#" -gt 0 ] && [ "$1" != -- ]; do
	dir=$1; shift
	[ -d "$dir" ] && [ -f "$dir/Makefile" ] || { echo "not a recipe: $dir" >&2; exit 2; }
	if grep -n 'gcc16' "$dir/Makefile" "$dir"/*.mk "$dir"/*.cmake 2>/dev/null; then
		echo "FAIL: $dir refers to GCC 16"; fail=1
	fi
done
if [ "$#" -gt 0 ]; then
	shift
	readelf=${1:?READELF}; shift
	for elf; do
		out=$("$readelf" -d "$elf")
		case "$out" in
		*gcc16*|*libgcc_s*|*libstdc++*|*libatomic*)
			echo "FAIL: $elf uses the GCC runtime:"; echo "$out" | grep -E 'RUNPATH|RPATH|NEEDED'; fail=1 ;;
		esac
	done
fi
[ "$fail" = 0 ] || exit 1
echo 'PASS: no GCC 16 paths'
