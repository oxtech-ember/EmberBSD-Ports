#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Exercise the patched consumer rule with a real MIG under parallel make.
set -eu
[ "$#" -eq 8 ] || {
    echo "usage: $0 MAKEFILE_IN GMAKE MIG MIGCOM CLANG DARWIN_SDK KRB5_SOURCE NEW_WORK" >&2
    exit 2
}
makefile=$1 make=$2 mig=$3 migcom=$4 cc=$5 sdk=$6 krb=$7 work=$8
for path in "$makefile" "$make" "$mig" "$migcom" "$cc" "$sdk" "$krb" "$work"; do
    case "$path" in /*) ;; *) echo 'absolute paths required' >&2; exit 2;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ]
mkdir -p "$work"
ccache=$krb/src/lib/krb5/ccache
[ -f "$ccache/kcmrpc.defs" ] && [ -f "$ccache/kcmrpc_types.h" ]
shell=$(command -v mksh)
case "$shell" in /*) ;; *) echo 'select mksh on PATH' >&2; exit 2;; esac
sed -n '/^MIG ?= mig$/,/^clean-unix::/p' "$makefile" | sed '$d' > "$work/Makefile"
grep -q '^kcmrpc.c: kcmrpc.h$' "$work/Makefile"
printf '#!%s\nprintf "x\\n" >> "$MIG_COUNT"\nsleep 1\nexec "$REAL_MIG" "$@"\n' "$shell" > "$work/count-mig"
chmod +x "$work/count-mig"
ln -s "$ccache/kcmrpc.defs" "$work/kcmrpc.defs"
MIGCC=$cc MIGCOM=$migcom SDKROOT=$sdk REAL_MIG=$mig MIG_COUNT=$work/count
export MIGCC MIGCOM SDKROOT REAL_MIG MIG_COUNT
cd "$work"
"$make" -j2 -f Makefile "srcdir=$ccache" "MIG=$work/count-mig" kcmrpc.h kcmrpc.c
[ "$(wc -l < count | tr -d ' ')" = 1 ]
[ -s kcmrpc.h ] && [ -s kcmrpc.c ]
rm kcmrpc.c
"$make" -j2 -f Makefile "srcdir=$ccache" "MIG=$work/count-mig" kcmrpc.c
[ "$(wc -l < count | tr -d ' ')" = 2 ]
[ -s kcmrpc.h ] && [ -s kcmrpc.c ]
# A failed migcom must not replace an older KCM pair; retry must recover.
printf 'old header\n' > kcmrpc.h
printf 'old user\n' > kcmrpc.c
printf '#!%s\n"$REAL_MIGCOM" "$@" || exit $?\nexit 9\n' "$shell" > fail-migcom
chmod +x fail-migcom
REAL_MIGCOM=$migcom; export REAL_MIGCOM
MIGCOM=$work/fail-migcom; export MIGCOM
if "$make" -B -j2 -f Makefile "srcdir=$ccache" "MIG=$work/count-mig" kcmrpc.h kcmrpc.c; then
    echo 'consumer accepted a failed generator' >&2
    exit 1
fi
[ "$(cat kcmrpc.h)" = 'old header' ]
[ "$(cat kcmrpc.c)" = 'old user' ]
MIGCOM=$REAL_MIGCOM; export MIGCOM
"$make" -B -j2 -f Makefile "srcdir=$ccache" "MIG=$work/count-mig" kcmrpc.h kcmrpc.c
[ -s kcmrpc.h ] && [ -s kcmrpc.c ]
"$cc" -isysroot "$sdk" -std=gnu11 -Wall -Wextra -Werror \
    -I. -I"$ccache" -c kcmrpc.c -o kcmrpc.o
