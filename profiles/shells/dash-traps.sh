#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted trap lifetime regression.
set -eu
[ "$#" -eq 2 ] || { echo 'Usage: dash-traps.sh DASH NEW_WORK' >&2; exit 2; }
dash=$1
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
count=0
run()
{
    name=$1 expected_status=$2 expected_output=$3 program=$4
    status=0
    valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
        --errors-for-leak-kinds=definite,indirect,possible --track-origins=yes \
        --error-exitcode=97 --log-file="$work/$name-%p.log" \
        "$dash" -c "$program" > "$work/$name.stdout" 2> "$work/$name.stderr" || status=$?
    [ "$status" -eq "$expected_status" ] || {
        echo "FAIL: $name returned $status (expected $expected_status)" >&2; exit 1;
    }
    [ "$(cat "$work/$name.stdout")" = "$expected_output" ] || {
        echo "FAIL: $name output" >&2; exit 1;
    }
    # Forked shells may finish independently. Their errors must also fail,
    # even when a parent shell does not propagate the child's exit status.
    if grep -E 'ERROR SUMMARY: [1-9]|definitely lost: [1-9]|indirectly lost: [1-9]|possibly lost: [1-9]' \
        "$work/$name-"*.log; then
        echo "FAIL: $name memory diagnostics" >&2; exit 1
    fi
    count=$((count + 1))
}
run normal 3 cleanup 'trap "printf cleanup" 0; exit 3'
run nested_exit 7 '' 'trap "exit 7" 0; exit 0'
run syntax_error 2 '' 'trap '\''eval "if"'\'' 0; exit 0'
run child_reset 0 done:cleanup 'trap "printf :cleanup" 0; trap ": inherited" USR1; (:); printf done'
run trap_listing 0 kept 'trap ": marker" USR1; text=$(trap); case $text in *marker*) printf kept;; *) exit 1;; esac'
run trap_clear 0 cleared 'trap ": marker" USR1; text=$(trap - USR1); test -z "$text" || exit 1; trap - USR1; printf cleared'
run replace 0 replaced 'trap ": initial" USR1 USR2; trap ": replacement" USR1; trap - USR1 USR2; printf replaced'
run external 0 cleanup 'trap "printf cleanup" 0; /bin/true'
run replacement_exit 0 once 'trap '\''trap "printf twice" 0; printf once'\'' 0'
printf 'PASS: %s trap lifecycle cases under Memcheck.\n' "$count"
