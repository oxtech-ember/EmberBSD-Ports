#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake pipewire-netbsd-errno.sh PKGSRC MAKECONF
#
# NetBSD has no EBADFD and no ECHRNG. libpipewire's pipewire.c sets errno to
# EBADFD, and the spa audio headers raw-utils.h and dsd-utils.h return
# -ECHRNG, so the NetBSD build stopped in pipewire.c.o and impl-port.c.o.
# Configure multimedia/pipewire for the cross target and compile those two
# objects. The MAKECONF should set its own WRKOBJDIR.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/multimedia/pipewire" MAKECONF="$makeconf" "$@" </dev/null; }
[ "$(bm -V '${OPSYS}')" = NetBSD ] || { echo "$0: select a MAKECONF for a NetBSD build" >&2; exit 2; }
log=$(mktemp "${TMPDIR:-/tmp}/pipewire-errno.XXXXXX")
trap 'rm -f "$log"; bm clean >/dev/null 2>&1 || :' EXIT
bm clean >/dev/null 2>&1 || :
bm configure >"$log" 2>&1 || { tail -5 "$log"; echo "FAIL: configure"; exit 1; }
wrksrc=$(bm -V '${WRKSRC}')
make_env=$(bm -V '${MAKE_ENV}')
path=$(bm -V '${PATH}')
status=0
for o in src/pipewire/libpipewire-0.3.so.0.1610.0.p/pipewire.c.o \
	src/pipewire/libpipewire-0.3.so.0.1610.0.p/impl-port.c.o; do
	eval "env PATH=\"\$path\" $make_env ninja -C \"\$wrksrc/output\" \"\$o\"" >"$log" 2>&1 ||
		{ grep -m 3 'error:' "$log" || tail -3 "$log"; echo "FAIL: $o"; status=1; }
done
[ "$status" -eq 0 ] || exit 1
echo "PASS: libpipewire compiles without EBADFD and ECHRNG"
