#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A Clang cross bulk graph never reaches GCC16.
# BMAKE, MAKECONF and PKGSRCDIR select a prepared Clang cross tree as for
# scripts/cross-bulk.sh. PKGPATH is a package with target dependencies.
# It also checks that no GCC16_* input or GCC16 reference reaches a Clang
# parse, and that fetch and build skip GCC16 packages of a stale order.
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
# The Clang profile skips the GCC16 recipes and never asks for a GCC16 input:
# no reason may name a GCC16_* variable.
for gcc in lang/gcc16-runtime lang/gcc16-fortran-runtime lang/gcc16-fortran-devel; do
    "$BMAKE" -C "$PKGSRCDIR/$gcc" show-vars VARNAMES='PKG_SKIP_REASON PKG_FAIL_REASON' \
        < /dev/null > "$out/reasons" || { echo "FAIL: $gcc does not parse" >&2; exit 1; }
    [ -n "$(sed -n 1p "$out/reasons")" ] || { echo "FAIL: the Clang profile does not skip $gcc" >&2; exit 1; }
    if grep -q 'GCC16_' "$out/reasons"; then
        echo "FAIL: the Clang profile asks $gcc for GCC16 inputs:" >&2; cat "$out/reasons" >&2; exit 1
    fi
done
echo 'PASS: the Clang profile skips the GCC16 recipes without asking for GCC16 inputs'
# No compiler, dependency or flag variable of a Clang package refers to GCC16.
vars='DEPENDS BUILD_DEPENDS TOOL_DEPENDS PKGSRC_COMPILER PKGSRC_FORTRAN CC CXX CPP FC
    CONFIGURE_ENV MAKE_ENV CMAKE_CONFIGURE_ARGS EMBERBSD_CROSS_CMAKE_ARGS
    BUILDLINK_PASSTHRU_DIRS BUILDLINK_PASSTHRU_RPATHDIRS CWRAPPERS_APPEND.cc
    CWRAPPERS_APPEND.cxx CWRAPPERS_APPEND.f77 CFLAGS CXXFLAGS FFLAGS LDFLAGS
    PKG_SKIP_REASON PKG_FAIL_REASON'
gcc16_refs()
{
    MAKECONF=$1 "$BMAKE" -C "$PKGSRCDIR/$path" show-vars VARNAMES="$(echo $vars)" \
        < /dev/null > "$out/vars" || return 2
    grep -i 'gcc16' "$out/vars"
}
if gcc16_refs "$MAKECONF" > "$out/refs"; then
    echo "FAIL: Clang variables of $path refer to GCC16:" >&2; cat "$out/refs" >&2; exit 1
fi
[ -s "$out/vars" ] || { echo "FAIL: $path does not parse" >&2; exit 1; }
cat > "$out/mk-ref.conf" <<MAKE
.include "$MAKECONF"
.if \${PKGPATH:U} == "$path"
TOOL_DEPENDS+= gcc16-fortran-runtime>=16.2.0:../../lang/gcc16-fortran-runtime
CONFIGURE_ENV+= FC=\${GCC16_PREFIX:U/usr/pkg/gcc16}/bin/gfortran
.endif
MAKE
gcc16_refs "$out/mk-ref.conf" > "$out/refs-injected" || {
    echo 'FAIL: the scan misses injected GCC16 references' >&2; exit 1; }
[ "$(wc -l < "$out/refs-injected")" -ge 2 ] || {
    echo 'FAIL: the scan misses an injected GCC16 reference' >&2; cat "$out/refs-injected" >&2; exit 1; }
echo "PASS: no Clang variable of $path refers to GCC16; injected references are found"
# An order from an older tree may still name GCC16 packages. Fetch and build
# record them as skipped and never try them.
mkdir "$out/stale"
printf '%s\n' lang/gcc16-runtime lang/gcc16-fortran-runtime lang/gcc16-fortran-devel > "$out/stale/order"
: > "$out/stale/edges"
for mode in fetch build; do
    sh "$ports/scripts/cross-bulk.sh" "$mode" "$out/list" "$out/stale" > "$out/stale-$mode.log" 2>&1 || {
        echo "FAIL: $mode of a stale order failed" >&2; cat "$out/stale-$mode.log" >&2; exit 1; }
    for list_name in failed-fetch failed blocked; do
        if [ -s "$out/stale/$list_name" ]; then
            echo "FAIL: $mode tried GCC16 packages of a stale order:" >&2
            cat "$out/stale/$list_name" >&2; exit 1
        fi
    done
done
[ "$(grep -c '^lang/gcc16' "$out/stale/skipped")" -ge 6 ] || {
    echo 'FAIL: fetch and build do not record the skipped GCC16 packages' >&2; exit 1; }
echo 'PASS: fetch and build skip the GCC16 packages of a stale order'
