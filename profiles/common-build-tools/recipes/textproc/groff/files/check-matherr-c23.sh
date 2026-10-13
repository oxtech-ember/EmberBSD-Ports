#!/bin/sh
# Exercise the real matherr source with the legacy System V API contract.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 GROFF_SOURCE NEW_WORK" >&2
    exit 2
fi
source_dir=$(cd "$1" && pwd)
work=$2
cc=${CC:-clang}
test ! -e "$work"
mkdir -p "$work"
work=$(cd "$work" && pwd)
cat > "$work/math.h" <<'HEADER'
#ifndef EMBER_GROFF_TEST_MATH_H
#define EMBER_GROFF_TEST_MATH_H
struct exception { int type; };
#define SING 1
#define DOMAIN 2
#define OVERFLOW 3
#define UNDERFLOW 4
#define TLOSS 5
#define PLOSS 6
#endif
HEADER
cat > "$work/main.c" <<'SOURCE'
#include <errno.h>
#include "math.h"

int matherr(struct exception *);

int
main(void)
{
    const int kinds[] = { SING, DOMAIN, OVERFLOW, UNDERFLOW, TLOSS, PLOSS, 99 };
    const int errors[] = { EDOM, EDOM, ERANGE, ERANGE, ERANGE, ERANGE, 123 };
    unsigned int i;

    for (i = 0; i < sizeof(kinds) / sizeof(kinds[0]); i++) {
        struct exception exc = { kinds[i] };
        errno = 123;
        if (matherr(&exc) != 1 || errno != errors[i])
            return 1;
    }
    return 0;
}
SOURCE
"$cc" -std=gnu23 -Wall -Wextra -Werror -DHAVE_STRUCT_EXCEPTION=1 \
    -I"$work" -fsanitize=address,undefined -fno-omit-frame-pointer \
    "$source_dir/src/libs/libgroff/matherr.c" "$work/main.c" \
    -o "$work/matherr-test"
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 "$work/matherr-test"
echo 'PASS: C23 prototype and all System V errno branches (ASan/UBSan)'
