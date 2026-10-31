#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cross-longdouble.sh PKGSRC MAKECONF
#
# numpy/_core/meson.build runs a target program to learn the long double
# format unless the Meson cross file has a longdouble_format property, so a
# cross build stopped at "Can not run test applications in this cross
# environment". Write the recipe's cross file and compare the property
# with the format the target compiler predefines.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/math/py-numpy makeconf=$2
tmp=$(mktemp -d "${TMPDIR:-/tmp}/numpy-longdouble.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" \
	SKIP_DEPENDS=yes WRKDIR="$tmp/w" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
mkdir -p "$tmp/w"
bm "$tmp/w/.meson_cross" >"$tmp/cross.log" 2>&1 ||
	{ tail -5 "$tmp/cross.log"; echo "FAIL: Meson cross file"; exit 1; }
got=$(sed -n "s/^longdouble_format = '\(.*\)'\$/\1/p" "$tmp/w/.meson_cross")
cc=$(bm -V '${_EMBER_SDK_CC:U}')
[ -n "$cc" ] || cc=$(bm -V '${CC}')
target=$(bm -V '${MACHINE_GNU_PLATFORM}')
macros=$("$cc" --target="$target" -E -dM -x c /dev/null)
m() { printf '%s\n' "$macros" | sed -n "s/^#define $1 //p"; }
case $(m __LDBL_MANT_DIG__):$(m __SIZEOF_LONG_DOUBLE__) in
113:16)	want=IEEE_QUAD ;;
64:16)	want=INTEL_EXTENDED_16_BYTES ;;
64:12)	want=INTEL_EXTENDED_12_BYTES ;;
53:8)	want=IEEE_DOUBLE ;;
*)	echo "FAIL: unknown long double for $target"; exit 1 ;;
esac
case $(m __BYTE_ORDER__) in __ORDER_BIG_ENDIAN__) want=${want}_BE ;; *) want=${want}_LE ;; esac
[ "$got" = "$want" ] || { echo "FAIL: longdouble_format '${got:-none}', target has $want"; exit 1; }
echo "PASS: the numpy cross file names the target long double format ($want)"
