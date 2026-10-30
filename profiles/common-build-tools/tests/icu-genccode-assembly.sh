#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# ICU's configure lets genccode write assembly only for Linux, kFreeBSD,
# i386 BSD and GNU hosts. On aarch64 and amd64 NetBSD, pkgdata then wrote
# and compiled one C file per data item, one compiler run at a time: about
# 4300 runs for each of the static and shared libicudata, half an hour of
# a cross bulk build. The test applies the recipe's patch-configure to the
# configure of DISTFILE and runs its genccode check for NetBSD targets. With
# a host genccode and a target compiler and nm, it also assembles the "gcc"
# output for the target and checks the data symbol.
# Usage: icu-genccode-assembly.sh DISTFILE NEW_OUTPUT [GENCCODE CC NM]
set -eu
[ "$#" = 2 ] || [ "$#" = 5 ] ||
    { echo 'Usage: icu-genccode-assembly.sh DISTFILE NEW_OUTPUT [GENCCODE CC NM]' >&2; exit 2; }
distfile=$1 out=$2
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
[ ! -e "$out" ] || { echo 'NEW_OUTPUT exists' >&2; exit 2; }
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd -P)
fail() { echo "FAIL: $*" >&2; exit 1; }
mkdir -p "$out"
tar -xzf "$distfile" -C "$out" icu/source/configure
(cd "$out/icu/source" && patch -s < "$ports/pkgsrc/textproc/icu/patches/patch-configure") ||
    fail 'patch-configure does not apply'
# The check, from "GENCCODE_ASSEMBLY=" to its outer "esac".
awk '$0 == "GENCCODE_ASSEMBLY=" { on = 1 } on { print } on && $0 == "esac" { exit }' \
    "$out/icu/source/configure" > "$out/check.sh"
grep -q '^esac$' "$out/check.sh" || fail 'no genccode assembly check in configure'
for host in aarch64--netbsd x86_64--netbsd i486--netbsdelf; do
    got=$(GCC=yes host=$host sh -c '. "$1"; echo "$GENCCODE_ASSEMBLY"' sh "$out/check.sh")
    [ "$got" = '-a gcc' ] || fail "genccode assembly for $host is '$got', expected '-a gcc'"
done
got=$(GCC=yes host=aarch64-apple-darwin sh -c '. "$1"; echo "$GENCCODE_ASSEMBLY"' sh "$out/check.sh")
[ -z "$got" ] || fail "Darwin now gets '$got'"
if [ "$#" = 5 ]; then
    genccode=$3 cc=$4 nm=$5
    head -c 4096 /dev/zero > "$out/t.dat"
    (cd "$out" && "$genccode" -a gcc -e icudt_test -d . t.dat > /dev/null) || fail 'genccode -a gcc failed'
    "$cc" -c -o "$out/t.o" "$out/t_dat.S" || fail 'the target compiler rejects the genccode assembly'
    "$nm" "$out/t.o" | grep -q ' R icudt_test_dat$' || fail "no data symbol: $("$nm" "$out/t.o")"
fi
echo 'PASS: genccode writes assembly for NetBSD targets, and the target compiler assembles it'
