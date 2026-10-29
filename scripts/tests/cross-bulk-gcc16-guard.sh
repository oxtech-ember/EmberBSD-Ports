#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A Clang cross bulk graph never reaches GCC16.
# BMAKE, MAKECONF and PKGSRCDIR select a prepared Clang cross tree as for
# scripts/cross-bulk.sh. PKGPATH is a package with target dependencies.
set -eu
[ "$#" = 2 ] || { echo 'Usage: cross-bulk-gcc16-guard.sh PKGPATH NEW_OUTPUT' >&2; exit 2; }
path=$1 out=$2
: "${BMAKE:?}" "${MAKECONF:?}" "${PKGSRCDIR:?}"
case "$path$out$MAKECONF" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
family=$("$BMAKE" -C "$PKGSRCDIR/$path" show-var VARNAME=EMBERBSD_CROSS_COMPILER_FAMILY < /dev/null)
[ "$family" = clang ] || { echo "MAKECONF selects the $family cross family, not clang" >&2; exit 2; }
mkdir "$out"
# A complete local recipe list names the GCC16 packages beside ordinary ones.
printf '%s\n' "$path" lang/gcc16 lang/gcc16-runtime lang/gcc16-fortran-runtime \
    lang/gcc16-fortran-devel > "$out/list"
sh "$ports/scripts/cross-bulk.sh" order "$out/list" "$out/state" > "$out/order.log"
if grep -q '^lang/gcc16' "$out/state/order"; then
    echo 'FAIL: the Clang graph orders GCC16 packages:' >&2
    grep '^lang/gcc16' "$out/state/order" >&2; exit 1
fi
grep -qFx "$path" "$out/state/order" || { echo "FAIL: $path is not ordered" >&2; exit 1; }
[ "$(grep -c '^lang/gcc16' "$out/state/skipped")" = 4 ] || {
    echo 'FAIL: the GCC16 list entries are not recorded as skipped' >&2; exit 1; }
echo "PASS: the Clang graph of $path skips GCC16 list entries"
# Any package that reaches a GCC16 package refuses the whole graph.
cat > "$out/mk.conf" <<MAKE
.include "$MAKECONF"
.if \${PKGPATH:U} == "$path"
DEPENDS+= gcc16-runtime>=16.2.0:../../lang/gcc16-runtime
.endif
MAKE
echo "$path" > "$out/list-leak"
if MAKECONF=$out/mk.conf sh "$ports/scripts/cross-bulk.sh" order "$out/list-leak" "$out/leak" \
    > "$out/leak.log" 2> "$out/leak.err"; then
    echo 'FAIL: a Clang graph reaching GCC16 was ordered' >&2; exit 1
fi
grep -qFx "$path -> lang/gcc16-runtime" "$out/leak.err" || {
    echo 'FAIL: the refusal does not name the GCC16 dependency' >&2; cat "$out/leak.err" >&2; exit 1; }
[ ! -e "$out/leak/order" ] || { echo 'FAIL: an order was written for a refused graph' >&2; exit 1; }
echo "PASS: a Clang graph in which $path reaches GCC16 is refused"
