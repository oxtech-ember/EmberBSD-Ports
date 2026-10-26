#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the real CPython header with the selected C compiler.
set -eu
[ "$#" -eq 3 ] || { echo 'Usage: python-array-ice.sh PATCHED_HEADER PRISTINE_HEADER NEW_WORK' >&2; exit 2; }
: "${CC:?Set CC to the native or target C compiler executable}"
[ ! -e "$3" ] && [ ! -L "$3" ] || { echo 'Work exists.' >&2; exit 2; }
mkdir -p "$3/patched" "$3/pristine"
work=$(CDPATH= cd -- "$3" && pwd)
cp "$1" "$work/patched/pymacro.h"
cp "$2" "$work/pristine/pymacro.h"
cp "$(dirname -- "$1")/patchlevel.h" "$work/patchlevel.h"
"$CC" --version > "$work/compiler.txt"
"$CC" -dumpmachine >> "$work/compiler.txt"
cat > "$work/positive.c" <<'C'
#include <stddef.h>
#include <stdint.h>
#define PyAPI_FUNC(type) extern type
#define _Py_TYPEOF __typeof__
#include "patchlevel.h"
#include "pymacro.h"
int values[7];
enum { array_count = Py_ARRAY_LENGTH(values), assertion_zero = Py_BUILD_ASSERT_EXPR(1) };
unsigned char duplicates[Py_ARRAY_LENGTH(values)][3];
static const size_t count = Py_ARRAY_LENGTH(values);
_Static_assert(array_count == 7, "array length");
_Static_assert(assertion_zero == 0, "assertion result");
int main(void) { return count != 7 || sizeof(duplicates) != 21; }
C
cat > "$work/negative.c" <<'C'
#include <stddef.h>
#include <stdint.h>
#define PyAPI_FUNC(type) extern type
#define _Py_TYPEOF __typeof__
#include "patchlevel.h"
#include "pymacro.h"
#if defined(TEST_POINTER)
int *pointer;
unsigned char invalid[Py_ARRAY_LENGTH(pointer)];
#elif defined(TEST_FALSE)
enum { invalid = Py_BUILD_ASSERT_EXPR(0) };
#else
int check(int condition) { enum { invalid = Py_BUILD_ASSERT_EXPR(condition) }; return invalid; }
#endif
C
# Compile only. The same gate runs with the actual target headers and compiler.
for standard in gnu11 gnu17 gnu23; do
    # CFLAGS carries the caller's actual sysroot when testing a cross compiler.
    if "$CC" ${CFLAGS:-} -std="$standard" -Wall -Wextra -Werror -Wpedantic -I"$work/pristine" -c "$work/positive.c" -o "$work/pristine-$standard.o" > "$work/pristine-$standard.log" 2>&1; then
        echo 'Pristine header unexpectedly accepts integer constant-expression use.' >&2; exit 1
    fi
    grep -Eq 'variably modified|not an integer constant|not an integer constant expression|GNU extension' "$work/pristine-$standard.log"
    "$CC" ${CFLAGS:-} -std="$standard" -Wall -Wextra -Werror -Wpedantic -I"$work/patched" -c "$work/positive.c" -o "$work/patched-$standard.o" > "$work/patched-$standard.log" 2>&1
    for variant in POINTER FALSE RUNTIME; do
        if "$CC" ${CFLAGS:-} -std="$standard" -Wall -Wextra -Werror -Wpedantic -DTEST_$variant -I"$work/patched" -c "$work/negative.c" -o "$work/negative-$standard-$variant.o" > "$work/negative-$standard-$variant.log" 2>&1; then
            echo "Invalid $variant assertion accepted." >&2; exit 1
        fi
        grep -Eq 'static assertion|negative|not constant|not an integer constant' "$work/negative-$standard-$variant.log"
    done
done
printf '%s\n' 'PASS: selected compiler real header; pristine failure, array/enum/static expressions and invalid conditions.'
