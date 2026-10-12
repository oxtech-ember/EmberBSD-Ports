#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), exercise upstream KPackage fixtures with reviewed current expectations.
set -eu
[ "$#" = 3 ] || { echo 'Usage: kpackage-metadata.sh KPACKAGETOOL SOURCE NEW_WORK' >&2; exit 2; }
program=$1 source=$2 work=$3
for value in "$program" "$source" "$work"; do
    case "$value" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
done
mkdir "$work"
export LC_ALL=en_US.UTF-8
export XDG_DATA_DIRS="$source/src/kpackage/data"
for name in testfallbackpackage testpackage testpackage-nodisplay testpackagesdep testpackagesdepinvalid; do
    input=$source/autotests/data/$name
    output=$work/$name.appdata.xml
    if [ "$name" = testpackage ]; then
        (cd "$input" && "$program" --appstream-metainfo .) > "$output" 2> "$work/$name.log"
    else
        (cd "$input" && "$program" --appstream-metainfo . --appstream-metainfo-output "$output") > "$work/$name.stdout" 2> "$work/$name.log"
    fi
    if [ "$name" = testpackage-nodisplay ]; then
        [ ! -e "$output" ]
    else
        cmp "$input/$name.testappdataxml" "$output"
    fi
    printf 'PASS: %s\n' "$name"
done
if "$program" --appstream-metainfo "$work/missing-package" --appstream-metainfo-output "$work/missing.xml" > "$work/missing.log" 2>&1; then
    echo 'Missing metadata input was accepted' >&2; exit 1
fi
[ ! -e "$work/missing.xml" ]
echo 'PASS: current metadata bytes, NoDisplay omission and missing-input rejection'
