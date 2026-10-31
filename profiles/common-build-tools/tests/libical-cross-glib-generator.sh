#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake libical-cross-glib-generator.sh PKGSRC MAKECONF
#
# When CMAKE_CROSSCOMPILING, libical's src/libical-glib/CMakeLists.txt
# includes IMPORT_ICAL_GLIB_SRC_GENERATOR, the CMake export of a native
# ical-glib-src-generator. The cross recipe left it unset and configure
# stopped at ICAL_GLIB_SRC_GENERATOR-NOTFOUND. Require that a cross build of
# time/libical depends on the native package as a tool and imports the
# export file that the package's PLIST installs, together with the generator.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/time/libical" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
status=0
toolbase=$(bm -V '${TOOLBASE}')
case " $(bm -V '${TOOL_DEPENDS}') " in
*" libical"*":../../time/libical "*) ;;
*) echo "FAIL: no tool dependency on the native time/libical"; status=1;;
esac
# Read the unexpanded words: expanding all of CMAKE_CONFIGURE_ARGS
# hits the cross CMake arguments that refer back to it.
import=
for a in $(bm -V CMAKE_CONFIGURE_ARGS .MAKE.EXPAND_VARIABLES=no); do
	case $a in -DIMPORT_ICAL_GLIB_SRC_GENERATOR*=*) import=${a#*=};; esac
done
case $import in '${TOOLBASE}'/*) import=$toolbase/${import#'${TOOLBASE}'/};; esac
case $import in
"$toolbase"/*) ;;
*) echo "FAIL: IMPORT_ICAL_GLIB_SRC_GENERATOR is '${import}', not in TOOLBASE"; status=1;;
esac
plist=$pkgsrc/time/libical/PLIST
for f in "${import#"$toolbase"/}" libexec/libical/ical-glib-src-generator; do
	[ -n "$f" ] && grep -qx "$f" "$plist" ||
		{ echo "FAIL: native package does not install ${f:-the import file}"; status=1; }
done
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross libical imports the native ical-glib-src-generator"
