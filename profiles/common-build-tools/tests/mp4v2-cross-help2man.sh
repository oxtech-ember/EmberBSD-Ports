#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake mp4v2-cross-help2man.sh PKGSRC MAKECONF NEW_WORK
#
# multimedia/mp4v2 makes its manual pages with help2man from ./mp4art and
# the other utilities it has just linked. In a cross build those are target
# executables, help2man cannot run them and the build stopped. Require that
# a cross build depends on help2man and the native package as tools and
# passes HELP2MAN.bindir=${TOOLBASE}/bin. Then build the utilities with the
# host compiler, replace ./mp4art with a target ELF stand-in, and require
# that the patched doc rule writes the page from the HELP2MAN.bindir copy.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 PKGSRC MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
[ ! -e "$work" ] || { echo "$0: $work exists" >&2; exit 2; }
pkg=$pkgsrc/multimedia/mp4v2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkg" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
status=0
toolbase=$(bm -V '${TOOLBASE}')
pkgname=$(bm -V '${PKGNAME}')
deps=" $(bm -V '${TOOL_DEPENDS}') "
case $deps in *" $pkgname:../../multimedia/mp4v2 "*) ;;
*) echo "FAIL: no tool dependency on the native $pkgname"; status=1;; esac
case $deps in *" help2man-"*":../../converters/help2man "*) ;;
*) echo "FAIL: no tool dependency on help2man"; status=1;; esac
case " $(bm -V '${MAKE_FLAGS}') " in
*" HELP2MAN.bindir=$toolbase/bin "*) ;;
*) echo "FAIL: MAKE_FLAGS does not select HELP2MAN.bindir=$toolbase/bin"; status=1;;
esac
grep -qx 'bin/mp4art' "$pkg/PLIST" && grep -qx 'man/man1/mp4art.1' "$pkg/PLIST" ||
	{ echo "FAIL: PLIST lacks bin/mp4art or man/man1/mp4art.1"; status=1; }

distfile=$(bm -V '${DISTDIR}/${DISTFILES}')
wrksrc=$(bm -V '${WRKSRC:T}')
sdk=$(bm -V '${OSX_SDK_PATH}')
mkdir -p "$work"
tar -xzf "$distfile" -C "$work"
src=$work/$wrksrc
for p in "$pkg"/patches/patch-*; do
	patch -s -d "$src" -p0 -N < "$p" >/dev/null ||
		{ echo "FAIL: $(basename "$p") does not apply"; exit 1; }
done
PATH=$toolbase/bin:/usr/bin:/bin
export PATH
[ -z "$sdk" ] || { SDKROOT=$sdk; export SDKROOT; }
(cd "$src" && CC=clang CXX=clang++ ./configure --disable-shared \
	>"$work/configure.log" 2>&1 && gmake mp4art >"$work/build.log" 2>&1) ||
	{ echo "FAIL: native mp4art build, see $work"; exit 1; }
grep -q '^FOUND_HELP2MAN *= *yes' "$src/GNUmakefile" ||
	{ echo "FAIL: configure did not select help2man"; exit 1; }
mkdir "$work/native"
cp -p "$src/mp4art" "$work/native/mp4art"
# A cross-linked utility: present and executable, but not a host program.
rm -f "$src/mp4art"
printf '\177ELF\002\001\001\000' > "$src/mp4art"
chmod +x "$src/mp4art"
page=doc/man/man1/mp4art.1
(cd "$src" && gmake "$page" HELP2MAN.bindir="$work/native" >"$work/man.log" 2>&1) ||
	{ echo "FAIL: help2man did not use HELP2MAN.bindir, see $work/man.log"; exit 1; }
grep -q '^mp4art .- manual page for mp4art' "$src/$page" &&
	grep -qx '.B mp4art' "$src/$page" && grep -q 'covr' "$src/$page" ||
	{ echo "FAIL: $page lacks the mp4art --help text"; exit 1; }
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross mp4v2 manual pages come from the native utilities"
