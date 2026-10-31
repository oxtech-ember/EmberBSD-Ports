#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake perl5-term-readkey-cross.sh PKGSRC MAKECONF TARGET_CC NEW_WORK
#
# TermReadKey's ReadKey.pm.PL bootstraps the XS it has just built to read
# blockoptions(), a compile-time constant. In a cross build that is a
# target library and the host perl stopped with a DynaLoader error. Run the
# cross MakeMaker route on the patched distfile, preprocess ReadKey.c with
# the target compiler as the recipe does, and require that ReadKey.pm.PL
# writes ReadKey.pm from the selected MAKE_ENV without loading the XS.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF TARGET_CC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 cc=$3
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$4"
work=$4
pkg=devel/p5-Term-ReadKey
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$pkg" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
xs_env=
for w in $(bm -V '${MAKE_ENV:MTERMREADKEY_PREPROCESSED_XS=*}'); do xs_env=$w; done
[ -n "$xs_env" ] || echo "FAIL: MAKE_ENV does not select TERMREADKEY_PREPROCESSED_XS"
host=$(bm -V '${EMBERBSD_CROSS_BUILD_PERL}')
python=$(bm -V '${EMBERBSD_CROSS_BUILD_PYTHON}')
target=$(bm -V '${EMBERBSD_PERL_TARGET_CONFIG}')
sysroot=$(bm -V '${EMBERBSD_CROSS_SYSROOT}')
make=$(bm -V '${MAKE_PROGRAM}')
params=$(bm -V '${MAKE_PARAMS:MPERL_*}')
distfile=$(bm -V '${DISTDIR}/${DISTFILES}')
tar -xzf "$distfile" -C "$work"
src=$(echo "$work"/TermReadKey-*)
for p in "$pkgsrc/$pkg"/patches/patch-*; do
	[ -f "$p" ] && (cd "$src" && patch -s -p0 < "$p")
done
"$python" -B "$pkgsrc/lang/perl5/files/prepare-build-config.py" --host-perl "$host" \
	--target-config "$target" --sysroot "$sysroot" --cc "$cc" --ld "$cc" \
	--ar "${cc%clang}ar" --ranlib "${cc%clang}ranlib" --cflags=-O2 --ldflags= \
	--output "$work/config.json"
(
	cd "$src"
	unset PERL5OPT
	EMBERBSD_PERL_BUILD_CONFIG=$work/config.json
	export EMBERBSD_PERL_BUILD_CONFIG
	# shellcheck disable=SC2086
	"$host" Makefile.PL $params > "$work/build.log" 2>&1 &&
	"$make" cchars.h ReadKey.c >> "$work/build.log" 2>&1 &&
	"$make" CPPRUN="$cc -E" ReadKey.i >> "$work/build.log" 2>&1
) || { echo "FAIL: cross MakeMaker configure or preprocess; see $work/build.log"; exit 1; }
(
	cd "$src"
	[ -z "$xs_env" ] || export "$xs_env"
	"$host" ReadKey.pm.PL ReadKey.pm >> "$work/build.log" 2>&1
) || { echo "FAIL: ReadKey.pm.PL needs the target XS; see $work/build.log"; exit 1; }
grep -q "^Target blockoptions from ReadKey.i: [0-9]" "$work/build.log" &&
	awk '/^# blockoptions:/ { b = 1 } b && /^sub ReadKey / { f = 1 } END { exit !f }' \
	"$src/ReadKey.pm" ||
	{ echo "FAIL: ReadKey.pm lacks the target blockoptions ReadKey"; exit 1; }
[ -n "$xs_env" ] || exit 1
echo "PASS: cross TermReadKey takes blockoptions from the target preprocessor"
