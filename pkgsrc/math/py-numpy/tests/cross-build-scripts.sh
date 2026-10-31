#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cross-build-scripts.sh PKGSRC MAKECONF
#
# Meson runs numpy/_build_utils/*.py and
# numpy/_core/code_generators/verify_c_api_version.py by their #! line.
# REPLACE_PYTHON gave them the target interpreter, which does not exist on
# the build machine, so a cross build stopped at "Could not execute
# command .../gitversion.py" and later at ".../verify_c_api_version.py";
# the cython link in pre-configure also named the target prefix. Run the
# recipe's interpreter replacement and substitutions without the target
# dependencies, then run the scripts as Meson does.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/math/py-numpy makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" SKIP_DEPENDS=yes "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
src=$(bm -V '${WRKSRC}') bl=$(bm -V '${BUILDLINK_DIR}')
trap 'bm clean >/dev/null 2>&1 || :' EXIT
bm clean >/dev/null 2>&1 || :
bm patch >/dev/null 2>&1 || { echo "FAIL: patch"; exit 1; }
mkdir -p "$bl/bin"
bm pre-configure replace-interpreter post-configure >/dev/null 2>&1 ||
	{ echo "FAIL: configure hooks"; exit 1; }
status=0
[ -x "$bl/bin/cython" ] || { echo "FAIL: cython -> $(readlink "$bl/bin/cython")"; status=1; }
# The scripts are not executable in the distfile; Meson then runs the
# interpreter named on the #! line, as run_script does here.
run_script() {
	interp=$(sed -n '1s/^#![ 	]*//p' "$src/$1")
	(cd "$src" && $interp "$@" >/dev/null 2>&1) ||
		{ echo "FAIL: $1: #!$interp"; status=1; }
}
run_script numpy/_build_utils/gitversion.py
run_script numpy/_build_utils/tempita.py --help
run_script numpy/_core/code_generators/verify_c_api_version.py --api-version \
	"$(sed -n "s/^C_API_VERSION = '\(.*\)'$/\1/p" "$src/numpy/_core/meson.build")"
[ "$status" -eq 0 ] || exit 1
echo "PASS: numpy build scripts and cython run on the build machine"
