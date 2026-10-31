#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake dbus-python-common-tool-python.sh PKGSRC MAKECONF
#
# sysutils/dbus-python-common passed the target PYTHONBIN to configure,
# whose AM_PATH_PYTHON check runs it on the build machine, so a cross
# build stopped with "/usr/pkg/bin/python3.15: inaccessible or not found".
# Run the recipe's PYTHON the way that check does.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/sysutils/dbus-python-common makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" -V "$1"; }
[ "$(bm '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
python=$(bm '${CONFIGURE_ARGS:MPYTHON=*:S/^PYTHON=//}')
"$python" -c 'import sys; sys.exit(sys.hexversion < 0x2010000)' >/dev/null 2>&1 ||
	{ echo "FAIL: configure cannot run PYTHON=$python"; exit 1; }
echo "PASS: dbus-python-common configure runs the build machine Python"
