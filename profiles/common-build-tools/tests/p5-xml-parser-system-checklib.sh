#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake p5-xml-parser-system-checklib.sh PKGSRC MAKECONF PERL NEW_WORKOBJDIR
#
# XML-Parser 2.59 bundles inc/Devel/CheckLib.pm, and Makefile.PL puts ./inc
# first in @INC. The bundled copy runs the target probe program in a cross
# build ("cannot execute binary file"), so the cross-aware
# p5-Devel-CheckLib>=1.16nb7 never loaded and expat was reported missing.
# Extract the recipe and require that Makefile.PL's @INC loads a
# Devel::CheckLib that has the cross check, not the bundled copy.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: BMAKE=bmake $0 PKGSRC MAKECONF PERL NEW_WORKOBJDIR" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 perl=$3 workobj=$4
case "$4" in /*) ;; *) echo "$0: NEW_WORKOBJDIR must be absolute" >&2; exit 2;; esac
mkdir "$4"
"$perl" -MDevel::CheckLib -e 'exit(Devel::CheckLib->can("_cross_build") ? 0 : 1)' ||
	{ echo "$0: PERL must have p5-Devel-CheckLib>=1.16nb7 installed" >&2; exit 2; }
mk() {
	MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/textproc/p5-XML-Parser" \
	    MAKECONF="$makeconf" WRKOBJDIR="$workobj" SKIP_DEPENDS=yes "$@"
}
wrksrc=$(mk -V '${WRKSRC}')
mk extract > "$workobj/extract.log" 2>&1 || { cat "$workobj/extract.log" >&2; exit 2; }
[ -f "$wrksrc/Makefile.PL" ] || { echo "$0: no Makefile.PL in $wrksrc" >&2; exit 2; }
got=$(cd "$wrksrc" && "$perl" -e 'use lib "./inc"; require Devel::CheckLib;
	print Devel::CheckLib->can("_cross_build") ? "cross-aware" : "bundled: $INC{q(Devel/CheckLib.pm)}"')
[ "$got" = cross-aware ] || { echo "FAIL: Makefile.PL loads the $got"; exit 1; }
echo "PASS: XML-Parser's Makefile.PL loads the cross-aware Devel::CheckLib"
