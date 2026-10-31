#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise production DHCP DAD transitions.
# Usage: dhcpcd-dad.sh PREPARED_SOURCE NEW_WORK [DHCP_SOURCE]
# DHCP_SOURCE selects an older dhcp.c for the negative control.
# Select CC, TEST_AWK and TEST_SHASUM explicitly. Set CFLAGS for the chosen
# target and DHCPCD_DAD_RUN=0 to only build.
# The host fixture substitutes OS/I/O calls. It is not a wire DHCP test.
set -eu
: "${CC:?select the compiler}" "${TEST_AWK:?select awk}" "${TEST_SHASUM:?select shasum}"
for tool in "$CC" "$TEST_AWK" "$TEST_SHASUM"; do
	case "$tool" in /*) ;; *) echo 'Tool paths must be absolute.' >&2; exit 2;; esac
done
[ "$#" -ge 2 ] && [ "$#" -le 3 ] || {
	printf 'usage: %s PREPARED_SOURCE NEW_WORK [DHCP_SOURCE]\n' "$0" >&2
	exit 2
}
root=$1
work=$2
source=${3:-$root/src/dhcp.c}
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
headers=$root/src
[ -f "$source" ] && [ -f "$headers/dhcp.h" ]
mkdir "$work"

# Retain upstream authorship and copy complete function bodies unchanged.
"$TEST_AWK" '/^#include/ { exit } { print }' "$source" > "$work/production.h"
for name in dhcp_discover dhcp_bind dhcp_finish_dad dhcp_arp_address dhcp_arp_bind \
    dhcp_lastlease dhcp_handleifa; do
	"$TEST_AWK" -v name="$name" '
	    $0 ~ "^" name "[(]" { print previous; copying = 1 }
	    copying { print }
	    copying && /^}/ { found = 1; exit }
	    { previous = $0 }
	    END { if (!found) exit 1 }
	' "$source" >> "$work/production.h"
done
"$TEST_AWK" '/^enum DHS/ { copying = 1 }
    copying { print }
    copying && /^};/ { found = 1; exit }
    END { if (!found) exit 1 }' "$headers/dhcp.h" > "$work/states.h"
"$TEST_AWK" '/^#define DHCPCD_(STATIC|INFORM|IPV4LL|TEST|CONFIGURE|BOOTP|REQUEST|MANAGER|ONESHOT)[[:space:]]/ { print }' \
    "$headers/if-options.h" > "$work/options.h"
"$TEST_AWK" '/^#define STATE_(EXPIRED|ADDED|FAKE)[[:space:]]/ { print }' \
    "$headers/ipv4.h" >> "$work/options.h"
printf 'DHCP source: %s\n' "$source"
"$TEST_SHASUM" -a 256 "$source"
"$CC" ${CFLAGS:--O2 -g -std=c11 -Wall -Wextra -Werror} \
    -I"$work" "$here/dhcpcd-dad.c" -o "$work/check"
if [ "${DHCPCD_DAD_RUN:-1}" = 1 ]; then
	"$work/check"
else
	printf 'Built target test: %s/check (not run)\n' "$work"
fi
