#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake netpbm-build-tools-cross.sh PKGSRC MAKECONF
#
# A Netpbm cross build compiles and runs buildtools/typegen on the build
# machine. It took the target CFLAGS and LDFLAGS, so the build machine
# linker rejected -zrelro and -R/usr/pkg/lib. Link and run a generator with
# the CC_FOR_BUILD, CFLAGS_FOR_BUILD and LDFLAGS_FOR_BUILD that the recipe
# passes to make, as buildtools/Makefile does.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/graphics/netpbm makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
CC_FOR_BUILD= CFLAGS_FOR_BUILD= LDFLAGS_FOR_BUILD=
eval "set -- $(bm -V '${MAKE_FLAGS:M*_FOR_BUILD=*}')"
for assignment; do
	case $assignment in
	CC_FOR_BUILD=*|CFLAGS_FOR_BUILD=*|LDFLAGS_FOR_BUILD=*)
		eval "${assignment%%=*}=\${assignment#*=}" ;;
	esac
done
[ -n "$CC_FOR_BUILD" ] || { echo "FAIL: no CC_FOR_BUILD"; exit 1; }
tmp=$(mktemp -d "${TMPDIR:-/tmp}/netpbm-build.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
printf '#include <stdio.h>\nint main(void) { puts("typegen"); return 0; }\n' >"$tmp/typegen.c"
# Word splitting of the flag variables is intended, as in make.
# shellcheck disable=SC2086
$CC_FOR_BUILD -c -o "$tmp/typegen.o" $CFLAGS_FOR_BUILD "$tmp/typegen.c" &&
$CC_FOR_BUILD -o "$tmp/typegen" $LDFLAGS_FOR_BUILD "$tmp/typegen.o" &&
[ "$("$tmp/typegen")" = typegen ] ||
	{ echo "FAIL: build tool flags: $CFLAGS_FOR_BUILD | $LDFLAGS_FOR_BUILD"; exit 1; }
echo "PASS: Netpbm build tools link and run on the build machine"
