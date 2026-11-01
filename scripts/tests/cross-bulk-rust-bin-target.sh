#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A cross bulk graph has no target Rust
# compiler. lang/rust-bin is the build-host compiler: a cross order lists it
# as skipped even when the package list names it, keeps its native node for
# the Cargo tools, and refuses a target package that depends on it.
# BMAKE, MAKECONF and PKGSRCDIR select a prepared cross tree as for
# scripts/cross-bulk.sh. PKGPATH is a Cargo package (for example
# graphics/libimagequant).
set -eu
[ "$#" = 2 ] || { echo 'Usage: cross-bulk-rust-bin-target.sh PKGPATH NEW_OUTPUT' >&2; exit 2; }
path=$1 out=$2
: "${BMAKE:?}" "${MAKECONF:?}" "${PKGSRCDIR:?}"
case "$path$out$MAKECONF" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir "$out"
fail() { echo "FAIL: $*" >&2; exit 1; }
# A package list written before the cross Rust selection names lang/rust-bin.
printf '%s\n' "$path" lang/rust-bin > "$out/list"
BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$BMAKE \
    sh "$ports/scripts/cross-bulk.sh" order "$out/list" "$out/state" > "$out/order.log" 2> "$out/order.err" ||
    fail "order failed: [$(tail -n 5 "$out/order.err")]"
if grep -qx lang/rust-bin "$out/state/order"; then
    fail "the cross order builds the target lang/rust-bin: [$(grep '^lang/rust-bin ' "$out/state/skipped" "$out/state/edges" | tr '\n' ';')]"
fi
grep -q '^lang/rust-bin ' "$out/state/skipped" || fail 'lang/rust-bin is not listed as skipped'
grep -qx lang/rust-bin@native "$out/state/order" || fail "$path lost its native rust-bin node"
grep -qx "lang/rust-bin@native $path" "$out/state/edges" || fail "no lang/rust-bin@native -> $path edge"
echo "PASS: the cross order skips the target lang/rust-bin and keeps the native one for $path"
# A target dependency on the build-host compiler is refused, with its name.
cat > "$out/mk-dep.conf" <<MAKE
.include "$MAKECONF"
.if \${PKGPATH:U} == "$path"
DEPENDS+= rust-bin-[0-9]*:../../lang/rust-bin
.endif
MAKE
if BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$BMAKE \
    MAKECONF=$out/mk-dep.conf sh "$ports/scripts/cross-bulk.sh" order "$out/list" "$out/dep" \
    > "$out/dep.log" 2> "$out/dep.err"; then
    fail 'a target dependency on lang/rust-bin was ordered'
fi
grep -qFx "$path -> lang/rust-bin" "$out/dep.err" ||
    fail "the refusal does not name the rust-bin dependency: [$(tail -n 5 "$out/dep.err")]"
[ ! -e "$out/dep/order" ] || fail 'an order was written for a refused graph'
echo "PASS: a target dependency of $path on lang/rust-bin is refused"
