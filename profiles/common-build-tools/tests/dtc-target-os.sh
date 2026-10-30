#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake GMAKE=gmake dtc-target-os.sh PKGSRC MAKECONF DISTFILE NEW_WORK
#
# The dtc Makefile selects the shared library rules from HOSTOS, which it
# takes from the build host uname. Evaluate the upstream Makefile with the
# recipe's MAKE_FLAGS and check that a NetBSD target gets the ELF rules.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF DISTFILE NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 distfile=$3 work=$4
[ ! -e "$work" ] || { echo "$0: $work already exists" >&2; exit 2; }
mkdir -p "$work"
recipe=$pkgsrc/sysutils/dtc
opsys=$(MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" -V OPSYS)
[ "$opsys" = NetBSD ] || { echo "$0: select a MAKECONF for a NetBSD target" >&2; exit 2; }
hostos=$(MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" \
	-V '${MAKE_FLAGS:MHOSTOS=*}')
xz -dc "$distfile" | tar -xf - -C "$work"
src=$(echo "$work"/dtc-*)
# -p prints the variables; the empty target keeps make from building.
# shellcheck disable=SC2086
ext=$(cd "$src" && "${GMAKE:-gmake}" -s -n -p -f Makefile $hostos .ember-none 2>/dev/null |
	sed -n 's/^SHAREDLIB_EXT *:*= *//p' | tail -n 1) || true
flags=$(cd "$src" && "${GMAKE:-gmake}" -s -n -p -f Makefile $hostos .ember-none 2>/dev/null |
	sed -n 's/^SHAREDLIB_LDFLAGS *:*= *//p' | tail -n 1) || true
case $ext:$flags in
so:*-soname,*) echo "PASS: dtc for $opsys builds libfdt.so ($flags)" ;;
*) echo "FAIL: dtc for $opsys selects .$ext with: $flags (${hostos:-no HOSTOS})"; exit 1 ;;
esac
