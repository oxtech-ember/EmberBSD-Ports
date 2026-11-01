#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake apache24-pcre2-config.sh PKGSRC MAKECONF PCRE2_PACKAGE
#
# In a cross build the httpd configure script looks only for
# ${target_alias}-pcre2-config; pkgsrc sets no target_alias, so a cross
# www/apache24 checked for "-pcre2-config" and stopped at "pcre(2)-config
# for libpcre not found". Stage the cross pcre2 binary package as the
# target prefix, prepare the pcre2-config copy for apache24 and run the
# queries of httpd's configure on it: --version must give a 10.x version,
# and the include and link flags must name the target prefix and not the
# staged one. Also check that native builds pass the installed script.
# MAKECONF selects a cross build.
set -eu
[ "$#" -eq 3 ] ||
	{ echo "Usage: $0 PKGSRC MAKECONF PCRE2_PACKAGE" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 pcre2pkg=$3
tmp=$(mktemp -d "${TMPDIR:-/tmp}/pcre2-config.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
# Point only the package paths (_CROSS_DESTDIR) at the staged prefix, and
# name the target LOCALBASE as the pcre2 prefix: the staged prefix has no
# package database.
bm() {
	dir=$1 cross=$2; shift 2
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/$dir" \
	    MAKECONF="$makeconf" WRKOBJDIR="$tmp/w-$cross" \
	    _CROSS_DESTDIR="$tmp/sysroot" \
	    ${prefix:+BUILDLINK_PREFIX.pcre2=$prefix} \
	    USE_CROSS_COMPILE=$cross "$@" </dev/null
}
prefix=
[ "$(bm www/apache24 yes -V '${USE_CROSS_COMPILE:Uno:tl}' 2>/dev/null)" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
prefix=$(bm www/apache24 yes -V '${LOCALBASE}' 2>/dev/null)
case $prefix in
/?*) ;;
*) echo "$0: no target LOCALBASE" >&2; exit 2;;
esac
mkdir -p "$tmp/sysroot$prefix"
tar -xzf "$pcre2pkg" -C "$tmp/sysroot$prefix" bin/pcre2-config
pc=$(bm www/apache24 yes -V '${PCRE2_CONFIG}' 2>/dev/null)
[ -n "$pc" ] ||
	{ echo "FAIL: the cross pcre2 buildlink3 file sets no PCRE2_CONFIG"; exit 1; }
env=$(bm www/apache24 yes -V '${CONFIGURE_ENV:MPCRE_CONFIG=*}' 2>/dev/null)
if [ "$env" != "PCRE_CONFIG=$pc" ]; then
	echo "FAIL: cross apache24 configures with '$env', not PCRE_CONFIG=$pc"
	exit 1
fi
if ! bm www/apache24 yes pcre2-cross-config >"$tmp/log" 2>&1; then
	echo "FAIL: preparing the cross pcre2-config copy failed:"
	sed 's/^/  /' "$tmp/log" | tail -5
	exit 1
fi
fail=0
case $("$pc" --version 2>/dev/null) in
1[0-9].*) ;;
*) echo "FAIL: apache24 configure rejects $pc"; exit 1;;
esac
cflags=$("$pc" --cflags) libs=$("$pc" --libs8)
case "$cflags $libs" in
*"$tmp"*) echo "FAIL: pcre2-config names the staged prefix: $cflags $libs"
	fail=1;;
esac
case " $cflags " in
*" -I$prefix/include "*) ;;
*) echo "FAIL: pcre2-config --cflags lost the target include directory: $cflags"
	fail=1;;
esac
case " $libs " in
*" -L$prefix/lib "*"-lpcre2-8 "*) ;;
*) echo "FAIL: pcre2-config --libs8 does not link the target libpcre2-8: $libs"
	fail=1;;
esac
prefix=
native=$(bm www/apache24 no -V '${CONFIGURE_ENV:MPCRE_CONFIG=*}' 2>/dev/null)
npc=$(bm www/apache24 no -V '${BUILDLINK_PREFIX.pcre2}' 2>/dev/null)
if [ "$native" != "PCRE_CONFIG=$npc/bin/pcre2-config" ]; then
	echo "FAIL: native apache24 configures with '$native'"
	fail=1
fi
[ "$fail" = 0 ] || exit 1
echo "PASS: cross apache24 runs a host pcre2-config copy; native passes the installed script"
