#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Usage: apache24-cross-apxs.sh BMAKE CROSS_MAKECONF EXPORTED_PKGSRC NEW_WORKOBJDIR
#
# Apache modules configure with --with-apxs2=APXS. In a cross build the
# apache24 buildlink3.mk named the target apxs under the target prefix, which
# the build host does not have, and ap-php's configure stopped. Prepare the
# consumer's apxs the way pre-configure does and require it to be a build-host
# program that answers with the sysroot httpd and with apr-1-config and
# apu-1-config programs that run on the build host.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 BMAKE CROSS_MAKECONF EXPORTED_PKGSRC NEW_WORKOBJDIR" >&2; exit 2; }
bmake=$1 conf=$2 pkgsrc=$3 work=$4
for path in "$bmake" "$conf" "$pkgsrc" "$work"; do
	case "$path" in /*) ;; *) echo 'Use absolute paths' >&2; exit 2 ;; esac
done
[ ! -e "$work" ] || { echo "NEW_WORKOBJDIR must be new: $work" >&2; exit 2; }
mkdir "$work"
mk() { MAKECONF=$conf "$bmake" -C "$pkgsrc/www/ap-php" MAKECONF="$conf" WRKOBJDIR="$work" "$@" </dev/null; }
fail() { echo "FAIL: $*"; exit 1; }
[ "$(mk show-var VARNAME=USE_CROSS_COMPILE | tr A-Z a-z)" = yes ] ||
	{ echo 'CROSS_MAKECONF must select a cross build' >&2; exit 2; }
apxs=$(mk show-var VARNAME=APXS)
mk _PKGSRC_BARRIER=yes apr-cross-config apu-cross-config >"$work/prepare.log" 2>&1 ||
	fail "preparing apr-1-config failed; see $work/prepare.log"
# The pre-configure step that prepares apxs; it is absent without the fix.
if mk -n _PKGSRC_BARRIER=yes apache-cross-apxs >/dev/null 2>&1; then
	mk _PKGSRC_BARRIER=yes apache-cross-apxs >>"$work/prepare.log" 2>&1 ||
		fail "preparing apxs failed; see $work/prepare.log"
fi
[ -x "$apxs" ] || fail "configure gets apxs $apxs, which the build host does not have"
q() { APR_LIBTOOL=libtool "$apxs" -q "$1" 2>"$work/apxs.err" || fail "apxs -q $1 failed"; }
sbindir=$(q SBINDIR)
[ -f "$sbindir/httpd" ] || fail "apxs names no httpd in $sbindir"
for v in APR_CONFIG APU_CONFIG; do
	prog=$(q "$v")
	"$prog" --version >/dev/null 2>&1 || fail "apxs $v $prog does not run on the build host"
done
[ ! -s "$work/apxs.err" ] || { cat "$work/apxs.err"; fail 'apxs reports errors'; }
echo "PASS: cross apache modules configure with a build-host apxs"
