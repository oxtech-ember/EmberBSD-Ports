#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake perl5-device-serialport-cross.sh PKGSRC MAKECONF TARGET_CC NEW_WORK
#
# Device::SerialPort's Makefile.PL runs ./configure for config.h. Without
# --host the configure script of a cross build tries to run a target program
# and stops with "cannot run C compiled programs". Apply the recipe's SUBST
# edits for Makefile.PL to the distfile, run the configure command that
# Makefile.PL then runs, with the target compiler, and require config.h.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF TARGET_CC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 cc=$3
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$4"
work=$4
pkg=comms/p5-Device-SerialPort
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$pkg" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
tar -xzf "$(bm -V '${DISTDIR}/${DISTFILES}')" -C "$work"
src=$(echo "$work"/Device-SerialPort-*)
for class in $(bm -V '${SUBST_CLASSES}'); do
	[ "$(bm -V "\${SUBST_FILES.$class}")" = Makefile.PL ] || continue
	eval "set -- $(bm -V "\${SUBST_SED.$class}")"
	sed "$@" "$src/Makefile.PL" > "$work/Makefile.PL" &&
		mv "$work/Makefile.PL" "$src/Makefile.PL"
done
command=$(sed -n 's|^system("\(\./configure[^"]*\)");.*|\1|p' "$src/Makefile.PL")
[ -n "$command" ] || { echo "FAIL: Makefile.PL does not run ./configure"; exit 1; }
# shellcheck disable=SC2086
(cd "$src" && CC=$cc $command > "$work/configure.log" 2>&1) ||
	{ echo "FAIL: '$command' with the target compiler: $(tail -2 "$work/configure.log" | head -1)"; exit 1; }
grep -q '^#define HAVE_TERMIOS_H 1' "$src/config.h" ||
	{ echo "FAIL: config.h lacks the target termios.h"; exit 1; }
echo "PASS: Makefile.PL configures config.h for the target ($command)"
