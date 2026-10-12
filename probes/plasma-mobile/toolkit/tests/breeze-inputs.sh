#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual cross recipe generator checks.
set -eu
[ "$#" = 3 ] || { echo 'Usage: breeze-inputs.sh PKGSRC HOST_PREFIX NEW_WORK' >&2; exit 2; }
pkgsrc=$1 host=$2
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set the cross MAKECONF}"
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
recipe=$pkgsrc/graphics/breeze-icons
"$BMAKE" -C "$recipe" "EMBERBSD_KF6_BREEZE_HOST=$host" emberbsd-native-breeze-check > "$work/valid.log" 2>&1
for kind in old missing-tool; do
    mkdir -p "$work/$kind/share" "$work/$kind/bin"
    printf '6.31.0\n' > "$work/$kind/share/ember-breeze-version"
    for tool in generate-symbolic-dark qrcAlias; do
        ln -s "$host/bin/$tool" "$work/$kind/bin/$tool"
    done
done
printf '6.30.0\n' > "$work/old/share/ember-breeze-version"
rm "$work/missing-tool/bin/qrcAlias"
for kind in old missing-tool absent; do
    if "$BMAKE" -C "$recipe" "EMBERBSD_KF6_BREEZE_HOST=$work/$kind" emberbsd-native-breeze-check > "$work/$kind.log" 2>&1; then
        echo "Invalid Breeze host tool accepted: $kind" >&2; exit 1
    fi
    grep -q 'Matching native Breeze 6.31 generators are required' "$work/$kind.log"
done
"$BMAKE" -C "$recipe" "EMBERBSD_KF6_BREEZE_HOST=$host" -V '${CMAKE_CONFIGURE_ARGS}' > "$work/cross.txt"
grep -Fq -- "-DGENERATE_SYMBOLIC_DARK=$host/bin/generate-symbolic-dark" "$work/cross.txt"
grep -Fq -- "-DQRC_ALIAS=$host/bin/qrcAlias" "$work/cross.txt"
"$BMAKE" -C "$recipe" USE_CROSS_COMPILE=no -V '${CMAKE_CONFIGURE_ARGS}' > "$work/native.txt"
! grep -q -- '-DGENERATE_SYMBOLIC_DARK=' "$work/native.txt"
echo 'PASS: native generators selected for cross only; missing and old tools rejected'
