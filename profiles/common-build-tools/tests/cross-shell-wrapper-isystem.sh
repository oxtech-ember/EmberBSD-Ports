#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise selected target shell wrappers.
set -eu
[ "$#" = 2 ] || { echo 'Usage: cross-shell-wrapper-isystem.sh WRAPPER_DIR NEW_WORK' >&2; exit 2; }
wrappers=$1 work=$2
case "$wrappers:$work" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
[ ! -e "$work" ] || { echo 'New work path required' >&2; exit 2; }
mkdir -p "$work/system headers" "$work/system, headers" "$work/quote headers" "$work/after headers"
printf '#define SELECTED_SYSTEM 73\nstatic inline int from_system(int unused) { return 7; }\n' > "$work/system headers/selected.h"
printf '#define SELECTED_COMMA 19\n' > "$work/system, headers/comma.h"
printf '#define SELECTED_QUOTE 13\n' > "$work/quote headers/quoted.h"
printf '#define SELECTED_AFTER 17\n' > "$work/after headers/after.h"
cat > "$work/check.c" <<'SRC'
#include <selected.h>
#include <comma.h>
#include "quoted.h"
#include <after.h>
#if SELECTED_SYSTEM != 73 || SELECTED_QUOTE != 13 || SELECTED_AFTER != 17 || SELECTED_COMMA != 19
#error unexpected header
#endif
int check(void) { return from_system(0) + SELECTED_SYSTEM + SELECTED_QUOTE + SELECTED_AFTER; }
SRC
printf 'int bad(int x, unsigned y) { return x < y; }\n' > "$work/consumer-warning.c"
for name in cc cxx; do
    compiler=$wrappers/$name
    WRAPPER_DEBUG=yes WRAPPER_LOG="$work/$name.log" "$compiler" -x "$([ "$name" = cc ] && printf c || printf c++)" \
        -Wall -Wextra -Werror -isystem "$work/system headers" -isystem "$work/system, headers" -iquote "$work/quote headers" \
        -idirafter "$work/after headers" -c "$work/check.c" -o "$work/$name.o"
    grep -F -- '-isystem ' "$work/$name.log" >/dev/null
    if WRAPPER_DEBUG=yes WRAPPER_LOG="$work/$name-warning.log" "$compiler" \
        -x "$([ "$name" = cc ] && printf c || printf c++)" -Wall -Wextra -Werror -c "$work/consumer-warning.c" -o "$work/$name-warning.o" >"$work/$name-warning.out" 2>&1; then
        echo "Consumer warning unexpectedly accepted: $name" >&2; exit 1
    fi
    grep -F 'sign-compare' "$work/$name-warning.out" >/dev/null
done
WRAPPER_DEBUG=yes WRAPPER_LOG="$work/cpp.log" "$wrappers/cpp" -isystem "$work/system headers" -isystem "$work/system, headers" \
    -iquote "$work/quote headers" -idirafter "$work/after headers" "$work/check.c" > "$work/preprocessed.c"
grep -F 'from_system' "$work/preprocessed.c" >/dev/null
grep -F -- '-isystem ' "$work/cpp.log" >/dev/null
# The generic transform/untransform preserves separators after a mapped subpath.
gen=$wrappers/../tmp/gen-transform
"$gen" transform 'I:/foo:/bar' > "$work/transform.sed"
"$gen" untransform 'I:/foo:/bar' > "$work/untransform.sed"
for suffix in ' path' ',tail' ';tail'; do
    actual=$(printf '%s\n' "-I/foo/sub$suffix" | sed -f "$work/transform.sed")
    [ "$actual" = "-I/bar/sub$suffix" ] || { echo 'Transform lost separator' >&2; exit 1; }
    actual=$(printf '%s\n' "-I/bar/sub$suffix" | sed -f "$work/untransform.sed")
    [ "$actual" = "-I/foo/sub$suffix" ] || { echo 'Untransform lost separator' >&2; exit 1; }
done
printf '%s\n' 'PASS: target C/C++/CPP system, quote, after includes and consumer warnings'
