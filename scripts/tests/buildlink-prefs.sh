#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A buildlink3.mk may be included before the
# package Makefile includes bsd.prefs.mk (net/grpc includes devel/abseil's
# first), so the variables that bsd.prefs.mk defines are not set yet there.
# A buildlink3.mk that tests one of them must first include
# ../../mk/bsd.fast.prefs.mk (or a file that includes it); otherwise the
# whole dependent package fails to parse with "Variable OPSYS is undefined".
# MACHINE_ARCH is not checked: bmake itself defines it.
# Usage: buildlink-prefs.sh [PKGSRC_OVERLAY]
set -eu
[ "$#" -le 1 ] || { echo 'Usage: buildlink-prefs.sh [PKGSRC_OVERLAY]' >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
tree=${1:-$root/pkgsrc}
[ -d "$tree" ] || { echo "No recipe tree: $tree" >&2; exit 2; }
status=0 n=0
for f in "$tree"/*/*/buildlink3.mk; do
    [ -f "$f" ] || continue
    n=$((n + 1))
    # The first line that expands a bsd.prefs.mk variable without a :U
    # default, and whether a prefs include comes before it.
    bad=$(awk '
        /^[ \t]*#/ { next }
        /^\.[ \t]*include[ \t]+"[^"]*\/mk\/(bsd\.fast\.prefs|bsd\.prefs|pkg-build-options)\.mk"/ { exit }
        /\$\{(OPSYS|OPSYS_VERSION|LOWER_OPSYS|MACHINE_PLATFORM|OS_VERSION)[}:]/ {
            if ($0 !~ /\$\{(OPSYS|OPSYS_VERSION|LOWER_OPSYS|MACHINE_PLATFORM|OS_VERSION):U/) { print FNR ": " $0; exit } }
    ' "$f")
    [ -z "$bad" ] && continue
    echo "FAIL: ${f#"$tree"/}:$bad" >&2
    echo "  include \"../../mk/bsd.fast.prefs.mk\" before this line" >&2
    status=1
done
[ "$n" -gt 0 ] || { echo "No buildlink3.mk files in $tree" >&2; exit 2; }
[ "$status" = 0 ] || exit 1
echo "PASS: $n buildlink3.mk files include bsd.fast.prefs.mk before they test a bsd.prefs.mk variable"
