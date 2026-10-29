#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual cross recipe generator checks.
# The cross recipe takes its generators from TOOLBASE, which the
# graphics/breeze-icons-generators TOOL_DEPENDS package of the same release
# fills. This overrides TOOLBASE with a prepared generator prefix.
set -eu
[ "$#" = 3 ] || { echo 'Usage: breeze-inputs.sh PKGSRC GENERATOR_PREFIX NEW_WORK' >&2; exit 2; }
pkgsrc=$1 host=$2
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set the cross MAKECONF}"
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
recipe=$pkgsrc/graphics/breeze-icons
"$BMAKE" -C "$recipe" "TOOLBASE=$host" emberbsd-native-breeze-check > "$work/valid.log" 2>&1
mkdir -p "$work/missing-tool/bin"
ln -s "$host/bin/generate-symbolic-dark" "$work/missing-tool/bin/generate-symbolic-dark"
for kind in missing-tool absent; do
    if "$BMAKE" -C "$recipe" "TOOLBASE=$work/$kind" emberbsd-native-breeze-check > "$work/$kind.log" 2>&1; then
        echo "Invalid Breeze generator prefix accepted: $kind" >&2; exit 1
    fi
    grep -q 'Native Breeze .* generators are required' "$work/$kind.log"
done
"$BMAKE" -C "$recipe" "TOOLBASE=$host" -V '${CMAKE_CONFIGURE_ARGS}' > "$work/cross.txt"
grep -Fq -- "-DGENERATE_SYMBOLIC_DARK=$host/bin/generate-symbolic-dark" "$work/cross.txt"
grep -Fq -- "-DQRC_ALIAS=$host/bin/qrcAlias" "$work/cross.txt"
"$BMAKE" -C "$recipe" USE_CROSS_COMPILE=no -V '${CMAKE_CONFIGURE_ARGS}' > "$work/native.txt"
! grep -q -- '-DGENERATE_SYMBOLIC_DARK=' "$work/native.txt"
echo 'PASS: native generators selected for cross only; missing tools rejected'
