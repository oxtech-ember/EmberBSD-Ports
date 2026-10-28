#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Packages build with Clang; GCC is only a
# per-platform override whose minimum version follows USE_CXX_FEATURES.
# A recipe or its buildlink3.mk must not pin GCC_REQD.
# Usage: no-gcc-reqd.sh RECIPE_DIR...
set -eu
[ "$#" -gt 0 ] || { echo 'usage: no-gcc-reqd.sh RECIPE_DIR...' >&2; exit 2; }
fail=0
for dir; do
	[ -d "$dir" ] && [ -f "$dir/Makefile" ] || { echo "not a recipe: $dir" >&2; exit 2; }
	for f in "$dir"/Makefile*  "$dir"/*.mk; do
		[ -f "$f" ] || continue
		if grep -nE '^[[:space:]]*GCC_REQD[[:space:]]*\+?=' "$f"; then
			echo "FAIL: $f pins GCC_REQD"; fail=1
		fi
	done
done
[ "$fail" = 0 ] || exit 1
echo 'PASS: no GCC_REQD pins'
