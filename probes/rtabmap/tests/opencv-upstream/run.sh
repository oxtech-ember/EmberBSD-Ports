#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Run a bounded set of real upstream cases.
set -eu
[ "$#" = 2 ] || { echo 'Usage: run.sh BINARY NEW_RESULTS' >&2; exit 2; }
binary=$1 out=$2
for path do case "$path" in /*) ;; *) exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
filter=$(awk 'BEGIN { sep="" } NF { printf "%s%s",sep,$0; sep=":" }' "$recipe/selected-tests.txt")
expected=$(awk 'NF { ++count } END { print count }' "$recipe/selected-tests.txt")
mkdir -p "$out"
cd "$out"
status=0
if [ "${OPENCV_UPSTREAM_MEMCHECK:-0}" = 1 ]; then
    valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
        --errors-for-leak-kinds=definite,indirect,possible --track-origins=yes \
        --error-exitcode=99 --log-file="$out/memcheck.log" \
        "$binary" "--gtest_filter=$filter" "--gtest_output=xml:$out/tests.xml" \
        --test_threads=1 --test_seed=809564 > "$out/tests.log" 2>&1 || status=$?
    grep -F 'ERROR SUMMARY: 0 errors' "$out/memcheck.log" >/dev/null
else
    "$binary" "--gtest_filter=$filter" "--gtest_output=xml:$out/tests.xml" \
        --test_threads=1 --test_seed=809564 > "$out/tests.log" 2>&1 || status=$?
fi
printf '%s\n' "$status" > "$out/exit-status.txt"
[ "$status" = 0 ] || { cat "$out/tests.log" >&2; exit 1; }
awk -v expected="$expected" '
  /<testsuites / {
    if (index($0,"tests=\"" expected "\"") && index($0,"failures=\"0\"") &&
        index($0,"disabled=\"0\"") && index($0,"errors=\"0\"")) good=1
  }
  END { exit !good }
' "$out/tests.xml"
if grep -E '<skipped|custom_status[^>]*skip' "$out/tests.xml"; then exit 1; fi
echo "PASS: $expected selected upstream OpenCV cases"
