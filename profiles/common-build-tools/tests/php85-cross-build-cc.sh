#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake php85-cross-build-cc.sh PKGSRC MAKECONF
#
# php85 builds the opcache JIT helper minilua with BUILD_CC and runs it on the
# build machine. configure's default "gcc" was the target compiler wrapper in
# a cross build, and the build ran an aarch64 NetBSD minilua on the build
# host. Require that the cross recipe passes BUILD_CC and that a program
# built with it runs here.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/lang/php85" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
build_cc=
for a in $(bm -V '${CONFIGURE_ENV:MBUILD_CC=*}'); do build_cc=${a#BUILD_CC=}; done
[ -n "$build_cc" ] || { echo "FAIL: configure gets no BUILD_CC"; exit 1; }
tmp=$(mktemp -d "${TMPDIR:-/tmp}/php-build-cc.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
printf 'int main(void) { return 42; }\n' >"$tmp/probe.c"
# BUILD_CC is a command line that configure stores unquoted in the Makefile.
eval "$build_cc \"\$tmp/probe.c\" -o \"\$tmp/probe\"" >"$tmp/cc.log" 2>&1 ||
	{ tail -3 "$tmp/cc.log"; echo "FAIL: BUILD_CC '$build_cc' cannot build a program"; exit 1; }
status=0
"$tmp/probe" 2>/dev/null || status=$?
[ "$status" -eq 42 ] || { echo "FAIL: a BUILD_CC program does not run on the build machine"; exit 1; }
echo "PASS: cross php85 builds minilua with the build machine compiler"
