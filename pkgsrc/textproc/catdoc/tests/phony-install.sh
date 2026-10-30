#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake phony-install.sh PKGSRC MAKECONF
#
# catdoc ships an INSTALL file. On a case-insensitive build filesystem it
# also answers to "install", so a file-backed top-level install target is
# up to date and nothing is staged. Configure the recipe, ensure a file
# named "install" exists on any filesystem, and check that the top-level
# install still descends into the source directories.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/textproc/catdoc makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
bm configure >/dev/null 2>&1 || { echo "$0: bmake configure failed" >&2; exit 2; }
wrksrc=$(bm -V '${WRKSRC}') make=$(bm -V '${MAKE_PROGRAM}')
[ -e "$wrksrc/install" ] || : > "$wrksrc/install"
out=$(cd "$wrksrc" && "$make" -n install 2>&1) || true
case $out in
*"cd \$i; "*install*) echo "PASS: catdoc install runs its sub-makes with an install file present" ;;
*) printf 'FAIL: top-level install did nothing:\n%s\n' "$out"; exit 1 ;;
esac
