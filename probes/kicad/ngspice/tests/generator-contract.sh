#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
set -eu
[ "$#" = 3 ] || { echo 'Usage: generator-contract.sh ABS_CMPP ABS_SOURCE ABS_NEW_OUTPUT' >&2; exit 2; }
cmpp=$1
source=$2
output=$3
[ ! -e "$output" ] && [ ! -L "$output" ] || exit 2
mkdir "$output"
"$cmpp" -p "$source/src/xspice/icm/analog/modpath.lst" > "$output/paths.txt" 2> "$output/valid.log"
[ -s "$output/paths.txt" ]
# The source list is independent of the generator output and contains comments.
awk '!/^([[:space:]]*\*|[[:space:]]*$)/ {print $1}' \
    "$source/src/xspice/icm/analog/modpath.lst" | sort > "$output/expected.txt"
tr '[:space:]' '\n' < "$output/paths.txt" | sed '/^$/d' | sort > "$output/actual.txt"
cmp "$output/expected.txt" "$output/actual.txt"
status=0
"$cmpp" -p "$output/missing.lst" > "$output/missing.out" 2> "$output/missing.log" || status=$?
[ "$status" != 0 ]
[ -s "$output/missing.log" ]
printf '%s\n' 'PASS: native XSPICE generator has complete paths, success status and failing missing input'
