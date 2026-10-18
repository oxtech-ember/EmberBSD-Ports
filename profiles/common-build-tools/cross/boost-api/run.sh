#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed Boost package acceptance.
set -eu
[ "$#" = 2 ] || { echo 'Usage: sh run.sh BUNDLE NEW_LOG_DIRECTORY' >&2; exit 2; }
bundle=$(cd "$1" && pwd -P)
logs=$2
case "$logs" in /*) ;; *) echo 'Use an absolute log directory.' >&2; exit 2;; esac
test ! -e "$logs"
mkdir "$logs"
cd "$bundle"
while read -r expected path; do
    test "$(sha256 -q "$path")" = "$expected"
done < artifacts.sha256
while read -r expected path; do
    test "$(sha256 -q "$path")" = "$expected"
done < runtime.sha256
unset LD_LIBRARY_PATH LD_PRELOAD LD_PRELOAD_32 LD_PRELOAD_64 EMBER_BOOST_FORCE_FAILURE
export LC_ALL=C
for cycle in 1 2 3 4; do
    timeout 90 "$bundle/boost-api" --report_level=detailed --log_level=test_suite --color_output=no > "$logs/cycle-$cycle.log" 2>&1 || {
        cat "$logs/cycle-$cycle.log"
        exit 1
    }
    grep -F '5 test cases out of 5 passed' "$logs/cycle-$cycle.log" > /dev/null
    awk '/^LOADED: / { print $2 }' "$logs/cycle-$cycle.log" > "$logs/cycle-$cycle.loaded"
    test -s "$logs/cycle-$cycle.loaded"
    while IFS= read -r path; do
        awk -v path="$path" '$2 == path { found=1 } END { exit !found }' runtime.sha256
    done < "$logs/cycle-$cycle.loaded"
    while IFS= read -r path; do
        grep -F -x "$path" "$logs/cycle-$cycle.loaded" > /dev/null
    done < required-providers.txt
    test "$(awk '/\/libgcc_s[.]so[.]/ { count++ } END { print count+0 }' "$logs/cycle-$cycle.loaded")" = 1
    cat "$logs/cycle-$cycle.log"
done
status=0
EMBER_BOOST_FORCE_FAILURE=1 timeout 90 "$bundle/boost-api" --report_level=detailed --log_level=all --color_output=no > "$logs/negative.log" 2>&1 || status=$?
test "$status" = 201
grep -F 'intentional Boost.Test failure control' "$logs/negative.log" > /dev/null
echo 'PASS: 20 installed Boost API cases, four provider inventories and the real Boost.Test failure control.'
