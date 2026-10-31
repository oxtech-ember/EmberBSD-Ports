#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake perl5-xml-libxml-cross-link.sh PKGSRC MAKECONF TARGET_CC NEW_WORK
#
# XML::LibXML's Makefile.PL merges the flags of Alien::Base::Wrapper into the
# MakeMaker arguments. Alien::Base::Wrapper reads the Perl configuration of the
# build machine, so a cross build linked LibXML.so with the build machine's
# LDDLFLAGS: on a Darwin build machine "-bundle -undefined dynamic_lookup"
# made ld.lld link an executable and stop with "undefined symbol: main".
# Apply the recipe's SUBST edits for Makefile.PL to the distfile, run it as
# lang/perl5/module.mk does, and link a shared object with the target compiler
# and the LDDLFLAGS of the generated Makefile.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF TARGET_CC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 cc=$3
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$4"
work=$4
pkg=textproc/p5-XML-LibXML
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$pkg" MAKECONF="$makeconf" "$@" </dev/null; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
tar -xzf "$(bm -V '${DISTDIR}/${DISTFILES}')" -C "$work"
src=$(echo "$work"/XML-LibXML-*)
for class in $(bm -V '${SUBST_CLASSES}'); do
	[ "$(bm -V "\${SUBST_FILES.$class}")" = Makefile.PL ] || continue
	eval "set -- $(bm -V "\${SUBST_SED.$class}")"
	sed "$@" "$src/Makefile.PL" > "$work/Makefile.PL" &&
		mv "$work/Makefile.PL" "$src/Makefile.PL"
done
perl=$(bm -V '${_PERL5_BUILD_INTERPRETER}')
# The target Config that MakeMaker reads, as lang/perl5/build-context.mk
# prepares it.
"$(bm -V '${EMBERBSD_CROSS_BUILD_PYTHON}')" -B "$pkgsrc/lang/perl5/files/prepare-build-config.py" \
	--host-perl "$(bm -V '${EMBERBSD_CROSS_BUILD_PERL}')" \
	--target-config "$(bm -V '${EMBERBSD_PERL_TARGET_CONFIG}')" \
	--sysroot "$(bm -V '${EMBERBSD_CROSS_SYSROOT}')" --cc "$cc" --ld "$cc" \
	--ar "$(bm -V '${AR}')" --ranlib "$(bm -V '${RANLIB}')" \
	--cflags="$(bm -V '${CFLAGS}')" --ldflags="$(bm -V '${LDFLAGS}')" \
	--output "$work/build-config.json" > "$work/build-config.log" 2>&1 ||
	{ echo "FAIL: target Perl build config: $(tail -1 "$work/build-config.log")"; exit 1; }
eval "set -- $(bm -V '${MAKE_PARAMS:Q}')"
(cd "$src" && EMBERBSD_PERL_BUILD_CONFIG=$work/build-config.json PERL_MM_USE_DEFAULT=1 LC_ALL=C \
	"$perl" Makefile.PL "$@" > "$work/Makefile.PL.log" 2>&1) ||
	{ echo "FAIL: Makefile.PL: $(tail -1 "$work/Makefile.PL.log")"; exit 1; }
lddlflags=$(sed -n 's/^LDDLFLAGS = //p' "$src/Makefile")
echo 'int ember_xml_libxml_probe(void) { return 0; }' > "$work/probe.c"
# shellcheck disable=SC2086
"$cc" -fPIC -c "$work/probe.c" -o "$work/probe.o" &&
	"$cc" $lddlflags "$work/probe.o" -o "$work/probe.so" > "$work/link.log" 2>&1 ||
	{ echo "FAIL: target link with LDDLFLAGS '$lddlflags': $(grep -m1 error "$work/link.log")"; exit 1; }
echo "PASS: LibXML.so links for the target with LDDLFLAGS '$lddlflags'"
