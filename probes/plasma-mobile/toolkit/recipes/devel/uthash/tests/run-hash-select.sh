#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
set -eu
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 UTHASH_SOURCE WORK_DIR" >&2
    exit 2
fi
source=$1
work=$2
[ -f "$source/src/uthash.h" ] || { echo 'Missing uthash.h' >&2; exit 2; }
[ ! -e "$work" ] || { echo 'WORK_DIR must not exist' >&2; exit 2; }
mkdir -p "$work"
source=$(cd "$source" && pwd)
work=$(cd "$work" && pwd)
tests=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cc=${CC:-cc}
cxx=${CXX:-c++}
for mode in c c-no-decltype cxx cxx-no-decltype; do
    compiler=$cc
    set -- -std=c11
    case "$mode" in
        cxx*) compiler=$cxx; set -- -x c++ -std=c++17 ;;
    esac
    case "$mode" in
        *no-decltype) set -- "$@" -DNO_DECLTYPE ;;
    esac
    "$compiler" "$@" -Wall -Wextra -g -fsanitize=address,undefined \
        -fno-omit-frame-pointer -I"$source/src" \
        "$tests/hash-select-test.c" -o "$work/$mode"
    ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
        "$work/$mode"
    printf 'PASS: %s\n' "$mode"
done
