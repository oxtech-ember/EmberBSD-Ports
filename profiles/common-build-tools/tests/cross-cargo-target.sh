#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cross-cargo-target.sh PKGSRC MAKECONF
#
# emberbsd-cargo.mk passes EMBER_CARGO_TARGET to cargo-config.py, which
# rejects an empty triple in cross mode. Recipes such as devel/mimalloc
# and devel/cxxbridge leave the triple to the cross profile, so the
# profile must answer it for the selected platform. Native builds keep
# the host triple (empty), and recipes with their own answer must agree.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
v() { d=$1; shift; MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$d" MAKECONF="$makeconf" "$@" -V '${EMBER_CARGO_TARGET}'; }
[ "$(MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/devel/mimalloc" MAKECONF="$makeconf" -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
status=0
for d in devel/mimalloc devel/cxxbridge devel/temporal-capi; do
	t=$(v "$d")
	[ "$t" = aarch64-unknown-netbsd ] ||
		{ echo "FAIL: $d cross Rust target is '$t'"; status=1; }
done
t=$(v devel/mimalloc USE_CROSS_COMPILE=no)
[ -z "$t" ] || { echo "FAIL: native Rust target is '$t'"; status=1; }
[ "$status" -eq 0 ] || exit 1
echo "PASS: the cross profile selects the platform Rust target"
