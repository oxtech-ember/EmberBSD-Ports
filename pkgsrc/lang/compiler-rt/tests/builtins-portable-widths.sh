#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual prepared compiler-rt builtins tests.
set -eu
: "${CC:?select CC with SDK run-native-check}"
: "${PYTHON:?select Python with SDK run-native-check}"
[ "$#" -eq 4 ] || { echo "usage: $0 PREPARED_SOURCE LINK_LAUNCHER LOCK_ROOT LOCK_CONTEXT" >&2; exit 2; }
src=$1; launcher=$2; lockroot=$3; context=$4
case "$src:$launcher:$lockroot:$context" in /*:/*:/*:/*) ;; *) exit 2 ;; esac
builtins=$src/compiler-rt/lib/builtins
unit=$src/compiler-rt/test/builtins/Unit
tests=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/compiler-rt-widths.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
for name in divmodsi4 udivsi3 umodsi3 udivdi3 umoddi3 udivmodti4 floattisf floatuntidf floatuntisf; do
    set -- "$builtins/$name.c"
    if [ "$name" = divmodsi4 ]; then set -- "$@" "$builtins/udivmodsi4.c" "$builtins/udivsi3.c"; fi
    "$PYTHON" -B "$launcher" --lock-root "$lockroot" --context "$context" -- \
        "$CC" -std=gnu11 -O2 -I"$builtins" "$unit/${name}_test.c" "$@" -o "$work/$name"
    result=$("$work/$name")
    if [ "$result" = skipped ]; then
        echo "SKIP: upstream $name (host prerequisites unavailable)"
    else
        [ -z "$result" ] || printf "%s\n" "$result"
        echo "PASS: upstream $name"
    fi
done
"$PYTHON" -B "$launcher" --lock-root "$lockroot" --context "$context" -- \
    "$CC" -std=gnu11 -O2 -I"$builtins" "$tests/builtins-portable-widths.c" \
    "$builtins/divmodsi4.c" "$builtins/udivmodsi4.c" "$builtins/udivsi3.c" \
    "$builtins/umodsi3.c" "$builtins/udivdi3.c" "$builtins/umoddi3.c" \
    "$builtins/floattisf.c" "$builtins/floatuntidf.c" "$builtins/floatuntisf.c" -o "$work/boundaries"
"$work/boundaries"
