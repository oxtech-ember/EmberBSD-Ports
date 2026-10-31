#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake git-base-cross-diff.sh PKGSRC MAKECONF
#
# git's configure picks DIFF from the build PATH, and git-sh-setup embeds
# it. In a cross build that was the build machine's gdiff, which does not
# exist on the target, and check-wrkref stopped the package. Configure the
# recipe without its dependencies and check the DIFF that git installs.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/devel/git-base makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" SKIP_DEPENDS=yes "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
src=$(bm -V '${WRKSRC}') toolbase=$(bm -V '${TOOLBASE}')
trap 'bm clean >/dev/null 2>&1 || :' EXIT
bm clean >/dev/null 2>&1 || :
bm configure >/dev/null 2>&1 || { echo "FAIL: configure"; exit 1; }
diff=$(sed -n 's/^DIFF *= *//p' "$src/config.mak.autogen")
case $diff in
""|"$toolbase"/*) echo "FAIL: DIFF = $diff"; exit 1 ;;
esac
echo "PASS: git uses the target diff ($diff)"
