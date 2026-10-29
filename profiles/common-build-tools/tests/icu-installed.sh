#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run prebuilt ICU acceptance on the target.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 CROSS_BUILT_TEST_DIRECTORY" >&2; exit 2; }
work=$(CDPATH= cd -- "$1" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
cd "$work"
pkg_info -e icu-79.1nb1 > package.log
if pkg_info -e 'icu-devel-[0-9]*' > sdk-package.log 2>&1; then
    echo 'The target must contain only the ICU runtime package' >&2; exit 1
fi
for tool in genbrk gencfu gencnval gendict genrb icu-config icuexportdata makeconv pkgdata; do
    test ! -e "/usr/pkg/bin/$tool"
done
for tool in escapesrc genccode gencmn gennorm2 gensprep icupkg; do
    test ! -e "/usr/pkg/sbin/$tool"
done
test ! -e /usr/pkg/include/unicode/utypes.h
icuinfo > icuinfo.log 2>&1
printf 'Ember \303\251 \360\237\214\237\n' > utf8.txt
uconv -f UTF-8 -t UTF-16LE utf8.txt > utf16.bin
uconv -f UTF-16LE -t UTF-8 utf16.bin > roundtrip.txt
cmp utf8.txt roundtrip.txt
# The matching native package generated these resources on the host.
test -s en.res
test -s emberprobe.dat
derb -c -s "$work" en > resource.log 2>&1
grep -q '42' resource.log
ldd consumer > loader.log 2>&1
if grep -q 'not found' loader.log; then cat loader.log; exit 1; fi
./consumer "$work"
printf '%s\n' 'PASS: installed ICU runtime conversion, collation, host-built resources and cross-built consumer'
