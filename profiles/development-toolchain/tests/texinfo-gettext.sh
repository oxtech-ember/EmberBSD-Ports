#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual Texinfo header-order and context contract.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 TEXINFO_SOURCE CC NEW_WORK" >&2; exit 2; }
source=$1 cc=$2 work=$3
[ "$(uname -s)" = NetBSD ] || { echo 'Run against native NetBSD libintl.' >&2; exit 2; }
for path in "$source" "$cc" "$work"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
done
[ -f "$source/tta/C/texi2any.c" ] && [ -f "$source/gnulib/lib/gettext.h" ] && [ -x "$cc" ]
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Output exists.' >&2; exit 2; }
mkdir "$work"
cat > "$work/check.c" <<'C'
#include <locale.h>
#include <stdio.h>
#include <string.h>
#include "includes.h"
static unsigned checks;
static int same(const char *actual, const char *expected)
{
    ++checks;
    if (strcmp(actual, expected) == 0) return 1;
    fprintf(stderr, "Expected [%s], got [%s]\n", expected, actual);
    return 0;
}
int main(void)
{
    const char *context = "fruit", *one = "apple", *many = "apples";
    if (!setlocale(LC_ALL, "C")) return 1;
    if (!same(gettext("plain"), "plain") ||
        !same(pgettext("fruit", "apple"), "apple") ||
        !same(npgettext("fruit", "apple", "apples", 1), "apple") ||
        !same(npgettext("fruit", "apple", "apples", 2), "apples") ||
        !same(pgettext_expr(context, one), "apple") ||
        !same(dcpgettext_expr("ember-texinfo-test", context, one, LC_MESSAGES), "apple") ||
        !same(dnpgettext_expr("ember-texinfo-test", context, one, many, 0), "apples") ||
        !same(dcnpgettext_expr("ember-texinfo-test", context, one, many, 1, LC_MESSAGES), "apple")) return 1;
    printf("PASS: %u gettext/context/plural checks\n", checks);
    return 0;
}
C
# Extract each production ordering without shadowing native system headers.
for file in tta/C/texi2any.c tta/C/convert/texinfo.c tta/C/main/txi_config.c tta/C/main/translations.c; do
    awk '/^#include <libintl.h>/ {print}
        /^#include "gettext.h"/ {print; done=1; exit}
        END {if (!done) exit 1}' "$source/$file" > "$work/includes.h"
    printf '%s\n' "$file"
for nls in 0 1; do
    "$cc" -std=c11 -O2 -Wall -Wextra -Werror -DENABLE_NLS=$nls \
        -iquote "$source/gnulib/lib" "$work/check.c" -lintl -o "$work/check-$nls"
    "$work/check-$nls"
done
done
