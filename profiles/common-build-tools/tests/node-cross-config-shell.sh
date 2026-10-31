#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake node-cross-config-shell.sh PKGSRC MAKECONF
#
# Node's configure is a Python script run through CONFIG_SHELL. It was the
# target PYTHONBIN, so a cross build stopped with "genv:
# '/usr/pkg/bin/python3.15': No such file or directory". Check that every
# Node recipe names an interpreter that runs on the build machine.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$1" MAKECONF="$makeconf" -V "$2"; }
[ "$(bm lang/nodejs '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
status=0
for recipe in lang/nodejs lang/nodejs22 lang/nodejs24; do
	[ -d "$pkgsrc/$recipe" ] || continue
	shell=$(bm "$recipe" '${CONFIG_SHELL}')
	"$shell" -c 'import sys' >/dev/null 2>&1 ||
		{ echo "FAIL: $recipe CONFIG_SHELL $shell"; status=1; }
done
[ "$status" -eq 0 ] || exit 1
echo "PASS: Node configure runs with the build machine Python"
