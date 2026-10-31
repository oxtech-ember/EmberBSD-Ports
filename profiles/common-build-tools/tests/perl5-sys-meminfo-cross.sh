#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake perl5-sys-meminfo-cross.sh PKGSRC MAKECONF TARGET_CC NEW_WORK
#
# Sys::MemInfo's Makefile.PL selected its system source with $^O, the
# running perl's system. A cross build from Darwin compiled arch/darwin.xs
# for NetBSD and stopped at mach/mach_host.h. Run the cross MakeMaker route
# on the patched distfile and require the source for the target osname and
# a target ELF module.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF TARGET_CC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 cc=$3
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$4"
work=$4
pkg=sysutils/p5-Sys-MemInfo
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$pkg" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
host=$(bm -V '${EMBERBSD_CROSS_BUILD_PERL}')
python=$(bm -V '${EMBERBSD_CROSS_BUILD_PYTHON}')
target=$(bm -V '${EMBERBSD_PERL_TARGET_CONFIG}')
sysroot=$(bm -V '${EMBERBSD_CROSS_SYSROOT}')
make=$(bm -V '${MAKE_PROGRAM}')
params=$(bm -V '${MAKE_PARAMS:MPERL_*}')
distfile=$(bm -V '${DISTDIR}/${DISTFILES}')
tar -xzf "$distfile" -C "$work"
src=$(echo "$work"/Sys-MemInfo-*)
for p in "$pkgsrc/$pkg"/patches/patch-*; do
	[ -f "$p" ] && (cd "$src" && patch -s -p0 < "$p")
done
"$python" -B "$pkgsrc/lang/perl5/files/prepare-build-config.py" --host-perl "$host" \
	--target-config "$target" --sysroot "$sysroot" --cc "$cc" --ld "$cc" \
	--ar "${cc%clang}ar" --ranlib "${cc%clang}ranlib" --cflags=-O2 --ldflags= \
	--output "$work/config.json"
osname=$(EMBERBSD_PERL_BUILD_CONFIG=$work/config.json "$host" \
	-MExtUtils::MakeMaker::Config -e 'print $Config{osname}')
[ "$osname" = netbsd ] || { echo "$0: the target osname is $osname, not netbsd" >&2; exit 2; }
(
	cd "$src"
	unset PERL5OPT
	EMBERBSD_PERL_BUILD_CONFIG=$work/config.json
	export EMBERBSD_PERL_BUILD_CONFIG
	# shellcheck disable=SC2086
	"$host" Makefile.PL $params > "$work/build.log" 2>&1
) || { echo "FAIL: Makefile.PL; see $work/build.log"; exit 1; }
cmp -s "$src/MemInfo.xs" "$src/arch/bsd.xs" && grep -q 'Sys::MemInfo for NetBSD' "$work/build.log" ||
	{ echo "FAIL: Makefile.PL did not select arch/bsd.xs for NetBSD"; exit 1; }
(
	cd "$src"
	EMBERBSD_PERL_BUILD_CONFIG=$work/config.json
	export EMBERBSD_PERL_BUILD_CONFIG
	"$make" >> "$work/build.log" 2>&1
) || { echo "FAIL: cross build; see $work/build.log"; exit 1; }
so=$src/blib/arch/auto/Sys/MemInfo/MemInfo.so
[ -f "$so" ] && "$host" -e 'open my $f, "<:raw", $ARGV[0] or die; read $f, my $h, 20;
	my ($m, $c, $d) = unpack "a4 C C", $h; my $e = unpack "v", substr($h, 18, 2);
	exit !($m eq "\x7fELF" && $c == 2 && $d == 1 && $e == 183)' "$so" ||
	{ echo "FAIL: no aarch64 ELF MemInfo.so"; exit 1; }
echo "PASS: cross Sys::MemInfo builds the source for the target system"
