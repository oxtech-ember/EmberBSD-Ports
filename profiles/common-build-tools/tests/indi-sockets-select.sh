#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake indi-sockets-select.sh PKGSRC MAKECONF
#
# libs/sockets/select.h used select() and struct timeval after including
# only <sys/socket.h>, which does not declare them on NetBSD, so misc/indi
# stopped with "field has incomplete type 'struct timeval'". Patch the
# recipe and compile the header alone with its target C++ compiler.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/misc/indi makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" SKIP_DEPENDS=yes "$@"; }
src=$(bm -V '${WRKSRC}') sysroot=$(bm -V '${CROSS_DESTDIR:U}')
if [ -n "$sysroot" ]; then cxx=$(bm -V '${TOOLDIR}/bin/${CXX}'); else cxx=$(bm -V '${CXX}'); fi
tmp=$(mktemp -d)
trap 'bm clean >/dev/null 2>&1 || :; rm -rf "$tmp"' EXIT
bm clean >/dev/null 2>&1 || :
bm patch >/dev/null 2>&1 || { echo "FAIL: patch"; exit 1; }
echo '#include "select.h"' > "$tmp/t.cc"
"$cxx" ${sysroot:+--sysroot="$sysroot"} -std=c++17 -Wall -Wextra -fsyntax-only \
    -I"$src/libs/sockets" -I"$src/libs" "$tmp/t.cc" ||
	{ echo "FAIL: libs/sockets/select.h does not compile alone"; exit 1; }
echo "PASS: INDI socket helpers declare select()"
