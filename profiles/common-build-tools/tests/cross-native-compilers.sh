#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real recipe generator compiler regression.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 EXPORTED_PKGSRC MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
bmake=${BMAKE:-bmake}
mkdir "$work"
"$bmake" -C "$pkgsrc/shells/bash" MAKECONF="$makeconf" show-vars \
    VARNAMES='PKG_FAIL_REASON EMBERBSD_CROSS_BUILD_CC NATIVE_CC EMBERBSD_CROSS_BUILD_CXX NATIVE_CXX CONFIGURE_ENV' \
    > "$work/bash.txt" 2> "$work/bash.stderr"
[ -z "$(sed -n '1p' "$work/bash.txt")" ]
[ "$(sed -n '2p' "$work/bash.txt")" = "$(sed -n '3p' "$work/bash.txt")" ]
[ "$(sed -n '4p' "$work/bash.txt")" = "$(sed -n '5p' "$work/bash.txt")" ]
# The recipe appends another CC_FOR_BUILD. Every assignment must name the
# selected host compiler, including the final assignment used by configure.
cc=$(sed -n '2p' "$work/bash.txt")
case "$cc" in /*) ;; *) exit 1;; esac
sed -n '6p' "$work/bash.txt" | tr ' ' '\n' | \
    awk -v expected="CC_FOR_BUILD=$cc" '
        /^CC_FOR_BUILD=/ { n++; if ($0 != expected) exit 1 }
        END { if (n < 2) exit 1 }'
for variable in NATIVE_CC NATIVE_CXX; do
    "$bmake" -C "$pkgsrc/shells/bash" MAKECONF="$makeconf" \
        "$variable=/bin/false" -v PKG_FAIL_REASON > "$work/$variable.txt"
    grep -q 'Cross generators require the selected native build compilers' "$work/$variable.txt"
done
echo 'PASS: actual Bash generator compiler assignments and overridden-compiler refusal'
