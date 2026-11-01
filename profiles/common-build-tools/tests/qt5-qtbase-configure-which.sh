#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake qt5-qtbase-configure-which.sh PKGSRC MAKECONF HOST_PREFIX NEW_WORK
#
# The qtbase configure script found awk and make with which(1). The native
# phase of a cross build runs with only the host tool prefix in PATH, which
# has no which(1), so configure set AWK to an empty string and stopped with
# "awk: command not found" while it created qmake. Patch configure with the
# recipe's patch-configure and run its tool detection with the PATH of the
# native qt5-qtbase build.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF HOST_PREFIX NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 host=$3
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$4"
work=$4
bm() {
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/x11/qt5-qtbase" \
	    MAKECONF="$makeconf" USE_CROSS_COMPILE=no _PKGSRC_BARRIER=yes \
	    WRKOBJDIR="$work/obj" \
	    "$@" </dev/null 2>/dev/null
}
distfile=$(bm -V '${DISTDIR}/${DISTFILES}')
src=$(bm -V '${DISTNAME:S/-opensource//}')
"$host/bin/bsdtar" -xf "$distfile" -C "$work" "$src/configure"
"$host/bin/gpatch" -s -d "$work/$src" -p0 -F0 < "$(bm -V '${PATCHDIR}')/patch-configure"
# The tool detection ends where configure checks the qmake variables.
sed '/^# make sure qmake is not confused/,$d' "$work/$src/configure" > "$work/head.sh"
echo 'echo "AWK=$AWK"; $AWK "BEGIN { exit 0 }" && echo awk-runs' >> "$work/head.sh"
path=$(bm -V '${PATH}')
if PATH=$path command -v which >/dev/null 2>&1; then
	echo "$0: the native PATH has which(1); the test cannot show the failure" >&2
	exit 2
fi
# shellcheck disable=SC2046 # the recipe's MAKE=... word.
out=$(cd "$work" && env -i PATH="$path" $(bm -V '${CONFIGURE_ENV:MMAKE=*}') \
    "$(bm -V '${CONFIG_SHELL}')" ./head.sh 2>&1) || true
out=$(echo "$out" | tr '\n' ' ')
case "$out" in
*"AWK= "*|*"AWK=") echo "FAIL: configure found no awk in the native PATH: $out"; exit 1 ;;
"AWK="?*" awk-runs ") echo "PASS: configure tool detection without which(1): $out" ;;
*) echo "FAIL: configure tool detection: $out"; exit 1 ;;
esac
