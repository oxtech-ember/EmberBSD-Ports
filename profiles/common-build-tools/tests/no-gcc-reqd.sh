#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Packages build with Clang; GCC is only a
# per-platform override, and the one-version policy provides only GCC16,
# which the override profile selects. No recipe, recipe include or
# buildlink3.mk may pin GCC_REQD. The lang/gcc16* recipes are exempt.
# Usage: no-gcc-reqd.sh --tree PORTS_ROOT
#        no-gcc-reqd.sh RECIPE_DIR...
set -eu
pin='^[[:space:]]*GCC_REQD[[:space:]]*\+?='
usage() { echo 'usage: no-gcc-reqd.sh --tree PORTS_ROOT | RECIPE_DIR...' >&2; exit 2; }
[ "$#" -gt 0 ] || usage
fail=0
check() {
	if grep -nE "$pin" "$1"; then
		echo "FAIL: $1 pins GCC_REQD"; fail=1
	fi
}
if [ "$1" = --tree ]; then
	[ "$#" = 2 ] || usage
	root=$2
	git -C "$root" rev-parse --show-toplevel > /dev/null 2>&1 ||
		{ echo "not a Git checkout: $root" >&2; exit 2; }
	list=$(mktemp)
	trap 'rm -f "$list"' EXIT
	# Tracked files only: the upstream pkgsrc submodule is not scanned.
	git -C "$root" ls-files -z | tr '\0' '\n' |
	    grep -E '(^|/)(Makefile[^/]*|[^/]*\.mk)$' |
	    grep -vE '(^|/)lang/gcc16[^/]*/' > "$list" || true
	[ -s "$list" ] || { echo "no recipe files under $root" >&2; exit 2; }
	n=0
	while IFS= read -r f; do
		check "$root/$f"; n=$((n + 1))
	done < "$list"
	[ "$fail" = 0 ] || exit 1
	echo "PASS: no GCC_REQD pins in $n recipe files"
	exit 0
fi
for dir; do
	[ -d "$dir" ] && [ -f "$dir/Makefile" ] || { echo "not a recipe: $dir" >&2; exit 2; }
	for f in "$dir"/Makefile* "$dir"/*.mk; do
		[ -f "$f" ] || continue
		check "$f"
	done
done
[ "$fail" = 0 ] || exit 1
echo 'PASS: no GCC_REQD pins'
