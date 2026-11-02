#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). apache24 NetBSD cross configuration regression.
# Configures www/apache24 for the cross target and generates server/test_char.h.
# Unpatched, configure stops at its void pointer length check, then at the
# libxml2 header probe, and the target gen_test_char cannot run on the host.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 BMAKE CROSS_MAKECONF EXPORTED_PKGSRC NEW_WORKOBJDIR" >&2; exit 2; }
bmake=$1 conf=$2 pkgsrc=$3 work=$4
for path in "$bmake" "$conf" "$pkgsrc" "$work"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths' >&2; exit 2;; esac
done
mkdir "$work"
mk() { MAKECONF=$conf "$bmake" -C "$pkgsrc/www/apache24" MAKECONF="$conf" WRKOBJDIR="$work" "$@" </dev/null; }
fail() { echo "FAIL: $*" >&2; exit 1; }
[ "$(mk show-var VARNAME=USE_CROSS_COMPILE | tr A-Z a-z)" = yes ] || { echo 'CROSS_MAKECONF must select a cross build' >&2; exit 2; }
mk configure >"$work/configure.log" 2>&1 || fail "configure failed; see $work/configure.log"
grep -q 'checking for void pointer length... (cached) no' "$work/configure.log" || fail 'void pointer length not preset'
grep -q 'checking for libxml2... yes' "$work/configure.log" || fail 'libxml2 headers not found'
wrksrc=$(mk show-var VARNAME=WRKSRC)
localbase=$(mk show-var VARNAME=LOCALBASE)
for script in apxs dbmmanage; do
    [ "$(sed -n '1s/^#!\([^ ]*\).*/\1/p' "$wrksrc/support/$script")" = "$localbase/bin/perl" ] ||
        fail "support/$script does not use the target perl"
done
make=$(mk show-var VARNAME=MAKE_PROGRAM)
flags=$(mk show-var VARNAME=MAKE_FLAGS)
# MAKE_FLAGS holds plain words (variable assignments without spaces).
# shellcheck disable=SC2086
(cd "$wrksrc/server" && "$make" $flags test_char.h) >"$work/test_char.log" 2>&1 || fail "test_char.h failed; see $work/test_char.log"
grep -q 'T_ESCAPE_SHELL_CMD' "$wrksrc/server/test_char.h" || fail 'test_char.h is incomplete'
[ ! -e "$wrksrc/server/gen_test_char" ] || fail 'the target gen_test_char was built'
echo "PASS: apache24 configures for the target and generates test_char.h on the build host"
