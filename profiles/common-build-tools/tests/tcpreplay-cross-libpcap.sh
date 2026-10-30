#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake tcpreplay-cross-libpcap.sh PKGSRC MAKECONF
#
# tcpreplay's configure finds libpcap only under the --with-libpcap
# directory, or else in fixed build-host directories, and checks each
# candidate with test -f on the build host. Prepare the buildlink tree of
# a cross build and check that the directory passed to configure holds
# the target libpcap header and shared library there.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
recipe=$pkgsrc/net/tcpreplay
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
dir=$(bm -V '${CONFIGURE_ARGS:M--with-libpcap=*:S/^--with-libpcap=//}' 2>/dev/null)
[ -n "$dir" ] || { echo "FAIL: no --with-libpcap; configure probes build-host directories"; exit 1; }
bm wrapper >/dev/null 2>&1 || { echo "$0: bmake wrapper failed" >&2; exit 2; }
status=0
for f in include/pcap.h lib/libpcap.so; do
	[ -f "$dir/$f" ] || { echo "FAIL: --with-libpcap=$dir has no $f on the build host"; status=1; }
done
[ "$status" -eq 0 ] || exit 1
echo "PASS: tcpreplay configure finds the target libpcap in $dir"
