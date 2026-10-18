#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors. Prepared with AI assistance.
set -eu
ulimit -c 0
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 BASELINE_CONSUMER PATCHED_CONSUMER NEW_OUTPUT_DIRECTORY" >&2
    exit 2
fi
baseline=$1
patched=$2
output=$3
valgrind=${VALGRIND:-valgrind}
[ -x "$baseline" ] && [ -x "$patched" ] || {
    echo "Both C consumers must exist" >&2
    exit 2
}
[ ! -e "$output" ] || {
    echo "The output directory must be new" >&2
    exit 2
}
mkdir -p "$output"
set +e
"$valgrind" --tool=memcheck --track-origins=yes --leak-check=full \
    --show-leak-kinds=all --errors-for-leak-kinds=all --error-exitcode=99 \
    "$baseline" > "$output/baseline-memcheck.log" 2>&1
baseline_status=$?
set -e
printf '%s\n' "$baseline_status" > "$output/baseline-status.txt"
[ "$baseline_status" -ne 0 ]
grep -q 'Invalid write' "$output/baseline-memcheck.log"
grep -q '_upb_Message_Copy' "$output/baseline-memcheck.log"
"$valgrind" --tool=memcheck --track-origins=yes --leak-check=full \
    --show-leak-kinds=all --errors-for-leak-kinds=all --error-exitcode=99 \
    "$patched" > "$output/patched-memcheck.log" 2>&1
grep -q 'PASS: UPB clone allocation failure returns NULL and preserves source' \
    "$output/patched-memcheck.log"
set +e
"$valgrind" --tool=memcheck --track-origins=yes --leak-check=full \
    --show-leak-kinds=all --errors-for-leak-kinds=all --error-exitcode=99 \
    "$baseline" --array-oom > "$output/baseline-array-memcheck.log" 2>&1
array_status=$?
set -e
printf '%s\n' "$array_status" > "$output/baseline-array-status.txt"
[ "$array_status" -eq 1 ]
grep -q 'clone reports success after array allocation failure; repeated field is absent' \
    "$output/baseline-array-memcheck.log"
grep -q 'ERROR SUMMARY: 0 errors' "$output/baseline-array-memcheck.log"
"$valgrind" --tool=memcheck --track-origins=yes --leak-check=full \
    --show-leak-kinds=all --errors-for-leak-kinds=all --error-exitcode=99 \
    "$patched" --array-oom > "$output/patched-array-memcheck.log" 2>&1
grep -q 'PASS: UPB array allocation failure propagates and preserves source' \
    "$output/patched-array-memcheck.log"
echo "PASS: UPB allocation failure no longer writes through a null clone"
echo "PASS: UPB repeated-field allocation failure no longer reports success"
for mode in string-oom string-copy-oom; do
    set +e
    "$valgrind" --tool=memcheck --track-origins=yes --leak-check=full \
        --show-leak-kinds=all --errors-for-leak-kinds=all --error-exitcode=99 \
        "$baseline" "--$mode" > "$output/baseline-$mode-memcheck.log" 2>&1
    string_status=$?
    set -e
    printf '%s\n' "$string_status" > "$output/baseline-$mode-status.txt"
    [ "$string_status" -ne 0 ]
    grep -q 'Invalid write' "$output/baseline-$mode-memcheck.log"
    grep -q 'upb_Clone_StringView' "$output/baseline-$mode-memcheck.log"
    "$valgrind" --tool=memcheck --track-origins=yes --leak-check=full \
        --show-leak-kinds=all --errors-for-leak-kinds=all --error-exitcode=99 \
        "$patched" "--$mode" > "$output/patched-$mode-memcheck.log" 2>&1
    grep -q 'PASS: UPB scalar string' "$output/patched-$mode-memcheck.log"
done
echo "PASS: UPB scalar string allocation failures propagate through both APIs"
