#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
set -eu
[ "$#" = 4 ] || { echo 'Usage: history-causal.sh PRISTINE PATCHED CLI_CONFIG_DIR NEW_OUTPUT' >&2; exit 2; }
pristine=$1
patched=$2
config=$3
output=$4
[ ! -e "$output" ] && [ ! -L "$output" ] || exit 2
mkdir "$output"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cc=${CC:-cc}
compile()
{
    source=$1
    destination=$2
    shift 2
    "$cc" ${CPPFLAGS:-} -O1 -g -std=gnu11 -ffunction-sections -fdata-sections \
        -I"$config/src/include" -I"$source/src/include" \
        "-DNGSPICE_HISTORY_SOURCE=\"$source/src/frontend/com_history.c\"" \
        "$here/history-contract.c" -Wl,--gc-sections "$@" -o "$destination"
}
compile "$pristine" "$output/baseline" -fsanitize=undefined -fno-sanitize-recover=all > "$output/baseline-build.log" 2>&1
status=0
"$output/baseline" > "$output/baseline-run.log" 2>&1 || status=$?
[ "$status" != 0 ]
grep 'runtime error: index .* out of bounds' "$output/baseline-run.log" >/dev/null
compile "$patched" "$output/patched-ubsan" -fsanitize=undefined -fno-sanitize-recover=all > "$output/patched-ubsan-build.log" 2>&1
"$output/patched-ubsan" > "$output/patched-ubsan-run.log" 2>&1
compile "$patched" "$output/patched" > "$output/patched-build.log" 2>&1
valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
    --errors-for-leak-kinds=all --error-exitcode=99 \
    --log-file="$output/memcheck.log" "$output/patched" > "$output/patched-run.log" 2>&1
printf '%s\n' 'PASS: actual history function overflow reproduced; repaired UBSan and Memcheck pass'
