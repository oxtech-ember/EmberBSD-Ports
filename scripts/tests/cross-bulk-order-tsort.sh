#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# scripts/cross-bulk.sh order sorts its graph with tsort. A curated PATH
# without tsort used to run every dependency query and then refuse the
# graph as cyclic. Order, selected-order and selected-build must refuse at
# once and name tsort; with tsort present the check must not stop them.
# Usage: cross-bulk-order-tsort.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-order-tsort.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
tsort=$(command -v tsort) || { echo 'The test host needs tsort' >&2; exit 2; }
sh=$(command -v sh)
# The PATH without tsort keeps every other command of the test host.
mkdir -p "$out/no-tsort" "$out/with-tsort"
for d in /bin /usr/bin; do
    for f in "$d"/*; do
        n=${f##*/}
        [ "$n" != tsort ] && [ -x "$f" ] && [ ! -e "$out/no-tsort/$n" ] || continue
        ln -s "$f" "$out/no-tsort/$n"
    done
done
ln -s "$tsort" "$out/with-tsort/tsort"
# The bmake stand-in records that a query ran and answers nothing.
printf '#!%s\n: > %s/queried\n' "$sh" "$out" > "$out/bmake"
chmod +x "$out/bmake"
echo t/a > "$out/list"
fail() { echo "FAIL: $*" >&2; exit 1; }
bulk() {
    dir=$1; shift
    env PATH="$dir" BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
        "$sh" "$ports/scripts/cross-bulk.sh" "$@"
}
for m in order selected-order selected-build; do
    status=0
    bulk "$out/no-tsort" $m "$out/list" "$out/state-$m" > "$out/$m.log" 2>&1 || status=$?
    [ "$status" = 2 ] || fail "$m without tsort exited $status: $(cat "$out/$m.log")"
    grep -qx 'The selected PATH must provide tsort for the dependency order' "$out/$m.log" ||
        fail "$m without tsort: $(cat "$out/$m.log")"
    [ ! -e "$out/queried" ] || fail "$m without tsort queried bmake"
    [ ! -e "$out/state-$m" ] || fail "$m without tsort created its state"
done
# With tsort the check passes; the stand-in then fails native verification.
bulk "$out/no-tsort:$out/with-tsort" order "$out/list" "$out/state-tsort" > "$out/tsort.log" 2>&1 || :
! grep -q 'must provide tsort' "$out/tsort.log" || fail "order with tsort: $(cat "$out/tsort.log")"
[ -e "$out/queried" ] || fail "order with tsort did not reach the native verification: $(cat "$out/tsort.log")"
echo 'PASS: order without tsort is refused before any query'
