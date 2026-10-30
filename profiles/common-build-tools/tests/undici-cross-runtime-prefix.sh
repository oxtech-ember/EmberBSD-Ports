#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake undici-cross-runtime-prefix.sh PKGSRC MAKECONF
#
# www/undici records the target path of its loader and refuses a cross
# build that does not select it. The cross profile selects the target
# LOCALBASE. Build the recipe with a cross MAKECONF and check the staged
# loader names that prefix, not the cross sysroot or the native TOOLBASE.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/www/undici makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
target=$(bm -V '${CROSS_LOCALBASE}') sysroot=$(bm -V '${CROSS_DESTDIR}') toolbase=$(bm -V '${TOOLBASE}')
case $target in /*) ;; *) echo "$0: CROSS_LOCALBASE is not absolute" >&2; exit 2 ;; esac
bm clean >/dev/null 2>&1 || :
log=$(mktemp "${TMPDIR:-/tmp}/undici.XXXXXX")
trap 'rm -f "$log"' EXIT
if ! bm build > "$log" 2>&1; then
	printf 'FAIL: cross build stopped:\n'; grep -E 'ERROR|Error' "$log" | head -5; bm clean >/dev/null 2>&1 || :; exit 1
fi
loader=$(bm -V '${WRKSRC}')/loader.js
status=0
grep -qF "\"$target/lib/node_modules/undici/loader.js\"" "$loader" ||
	{ echo "FAIL: loader does not use $target"; status=1; }
for p in "$sysroot" "$toolbase"; do
	! grep -qF "$p" "$loader" || { echo "FAIL: loader names the build host path $p"; status=1; }
done
bm clean >/dev/null 2>&1 || :
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross undici loader uses the target prefix $target"
