#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Exercise installed MIG using the consumer's unmodified KCM definitions.
set -eu
[ "$#" -eq 6 ] || {
    echo "usage: $0 MIG MIGCOM CLANG DARWIN_SDK KRB5_SOURCE NEW_WORK" >&2
    exit 2
}
mig=$1 migcom=$2 cc=$3 sdk=$4 krb=$5 work=$6
for path in "$mig" "$migcom" "$cc" "$sdk" "$krb" "$work"; do
    case "$path" in /*) ;; *) echo 'absolute paths required' >&2; exit 2;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ]
mkdir -p "$work"
cd "$work"
ccache=$krb/src/lib/krb5/ccache
[ -f "$ccache/kcmrpc.defs" ] && [ -f "$ccache/kcmrpc_types.h" ]
MIGCC=$cc MIGCOM=$migcom SDKROOT=$sdk; export MIGCC MIGCOM SDKROOT
"$mig" -header kcmrpc.h -user kcmrpc.c -sheader /dev/null \
    -server /dev/null -I"$ccache" "$ccache/kcmrpc.defs"
"$cc" -isysroot "$sdk" -std=gnu11 -Wall -Wextra -Werror \
    -I. -I"$ccache" -c kcmrpc.c -o kcmrpc.o

# A real preprocessor can emit output and still report failure.
mkdir negative
shell=$(command -v mksh)
case "$shell" in /*) ;; *) echo 'select mksh on PATH' >&2; exit 2;; esac
printf '#!%s\n"$REAL_CC" "$@" || exit $?\nexit 9\n' "$shell" > negative/fail-cc
chmod +x negative/fail-cc
REAL_CC=$cc; export REAL_CC
(
    cd negative
    MIGCC=$work/negative/fail-cc; export MIGCC
    if "$mig" -header kcmrpc.h -user kcmrpc.c -sheader /dev/null \
        -server /dev/null -I"$ccache" "$ccache/kcmrpc.defs"; then
        echo 'MIG accepted a failed preprocessor' >&2
        exit 1
    fi
    [ ! -e kcmrpc.h ] && [ ! -e kcmrpc.c ]
)

# Failed preprocessing must leave existing outputs untouched.
mkdir preserve
(
    cd preserve
    printf 'old header\n' > kcmrpc.h
    printf 'old user\n' > kcmrpc.c
    MIGCC=$work/negative/fail-cc; export MIGCC
    if "$mig" -header kcmrpc.h -user kcmrpc.c -sheader /dev/null \
        -server /dev/null -I"$ccache" "$ccache/kcmrpc.defs"; then exit 1; fi
    [ "$(cat kcmrpc.h)" = 'old header' ]
    [ "$(cat kcmrpc.c)" = 'old user' ]

)
