#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run prebuilt ICU acceptance on the target.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 CROSS_BUILT_TEST_DIRECTORY" >&2; exit 2; }
work=$(CDPATH= cd -- "$1" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
cd "$work"
[ "$(icu-config --version | sed 's/[[:space:]]*$//')" = 78.3 ]
[ "$(icu-config --cc | sed 's/[[:space:]]*$//')" = /usr/pkg/gcc16/bin/gcc ]
icuinfo > icuinfo.log 2>&1
printf 'Ember \303\251 \360\237\214\237\n' > utf8.txt
uconv -f UTF-8 -t UTF-16LE utf8.txt > utf16.bin
uconv -f UTF-16LE -t UTF-8 utf16.bin > roundtrip.txt
cmp utf8.txt roundtrip.txt
# Resource generation is a runtime tool check; no compiler runs on the board.
printf 'en { message { "Ember ICU probe" } answer:int { 42 } }\n' > en.txt
genrb -d "$work" en.txt > genrb.log 2>&1
printf 'en.res\n' > resources.txt
pkgdata -p emberprobe -m common -s "$work" -d "$work" resources.txt > pkgdata.log 2>&1
test -s emberprobe.dat
ldd consumer > loader.log 2>&1
if grep -q 'not found' loader.log; then cat loader.log; exit 1; fi
./consumer "$work"
printf '%s\n' 'PASS: installed ICU conversion, collation, resource generation and cross-built consumer'
