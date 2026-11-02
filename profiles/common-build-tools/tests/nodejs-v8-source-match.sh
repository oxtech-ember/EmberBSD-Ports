#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), Node V8 source dependency revision check.
# Evaluates the real lang/nodejs and lang/v8 recipes. No build runs.
set -eu
# MAKECONF is the caller's accepted Ports configuration for the tree.
[ "$#" = 5 ] || { echo 'Usage: nodejs-v8-source-match.sh EXPORTED_PKGSRC MAKECONF MAKE_WRAPPER PKG_ADMIN NEW_OUTPUT' >&2; exit 2; }
tree=$(CDPATH= cd -- "$1" && pwd)
makeconf=$2
make=$3
admin=$4
output=$5
[ ! -e "$output" ] && [ ! -L "$output" ] || exit 2
mkdir "$output"
MAKECONF="$makeconf" "$make" -C "$tree/lang/v8" -V 'pkg=${PKGNAME}' \
    -V 'version=${V8_VERSION}' > "$output/v8.log" 2>&1
MAKECONF="$makeconf" "$make" -C "$tree/lang/nodejs" -V 'deps=${TOOL_DEPENDS}' \
    > "$output/nodejs.log" 2>&1
package=$(sed -n 's/^pkg=//p' "$output/v8.log")
version=$(sed -n 's/^version=//p' "$output/v8.log")
[ -n "$package" ] && [ -n "$version" ] || { echo 'lang/v8 metadata is missing' >&2; exit 1; }
pattern=$(tr ' ' '\n' < "$output/nodejs.log" | sed -n 's/^\(v8-source[^:]*\):\.\.\/\.\.\/lang\/v8$/\1/p')
[ "$(printf '%s\n' "$pattern" | grep -c .)" = 1 ] || { echo 'Expected one lang/v8 TOOL_DEPENDS row' >&2; exit 1; }
# The current lang/v8 package, with or without its revision, satisfies Node.
for candidate in "$package" "v8-source-$version" "v8-source-${version}nb9"; do
    "$admin" pmatch "$pattern" "$candidate" || { echo "$pattern rejects $candidate" >&2; exit 1; }
done
# Another V8 release does not.
for candidate in "v8-source-${version}0" "v8-source-${version}.1" "v8-source-${version%.*}.$((${version##*.} + 1))"; do
    if "$admin" pmatch "$pattern" "$candidate"; then echo "$pattern accepts $candidate" >&2; exit 1; fi
done
echo "PASS: $pattern accepts $package and rejects other V8 releases"
