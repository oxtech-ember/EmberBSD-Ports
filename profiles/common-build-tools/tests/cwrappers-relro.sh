#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted regression for the cwrappers RELRO link rule.
# Usage: MAKECONF=CROSS_MK_CONF cwrappers-relro.sh EXPORTED_PKGSRC [PKGPATH]
# The default recipe www/http_load links without LDFLAGS. The test runs the
# wrapper phase and examines the generated cwrappers configuration files.
set -eu
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo "Usage: $0 EXPORTED_PKGSRC [PKGPATH]" >&2; exit 2; }
pkgsrc=$(CDPATH= cd -- "$1" && pwd)
pkgpath=${2:-www/http_load}
make=${BMAKE:-bmake}
dir=$pkgsrc/$pkgpath
fail() { echo "FAIL: $*" >&2; "$make" -C "$dir" clean >/dev/null 2>&1 || :; exit 1; }
var() { "$make" -C "$dir" show-var VARNAME="$1"; }
check() { # check MODE EXTRA_MAKE_ARGS...
    mode=$1; shift
    "$make" -C "$dir" clean >/dev/null 2>&1
    "$make" -C "$dir" "$@" wrapper >/dev/null 2>&1 || fail "wrapper phase of $pkgpath"
    cfg=$("$make" -C "$dir" "$@" show-var VARNAME=CWRAPPERS_CONFIG_DIR)
    use=$("$make" -C "$dir" "$@" show-var VARNAME=_PKGSRC_USE_RELRO)
    for w in cc c++ f77; do
        [ -f "$cfg/$w" ] || fail "no $w wrapper configuration"
        for f in $want; do
            for k in append_executable append_shared; do
                n=$(grep -cxF "$k=$f" "$cfg/$w" || :)
                if [ "$mode" = on ]; then
                    [ "$n" -ge 1 ] || fail "$w lacks $k=$f (relro=$use)"
                else
                    [ "$n" -eq 0 ] || fail "$w has $k=$f with relro=$use"
                fi
            done
        done
    done
    for w in cpp ld; do
        [ ! -f "$cfg/$w" ] || ! grep -q 'relro' "$cfg/$w" || fail "$w must not receive RELRO link flags"
    done
    echo "$mode: relro=$use flags=$want"
}
want=$(var _RELRO_LDFLAGS)
[ -n "$want" ] || fail "$pkgpath selects no RELRO flags; use a RELRO profile"
check on
check off PKGSRC_USE_RELRO=no
"$make" -C "$dir" clean >/dev/null 2>&1
echo "PASS: wrapped C, C++ and Fortran links receive the selected RELRO flags"
