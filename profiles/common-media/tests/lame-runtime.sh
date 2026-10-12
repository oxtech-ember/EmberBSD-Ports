#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Execute the installed CLI, with no audio I/O.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 VERIFIED_FIXTURES NEW_OUTPUT" >&2; exit 2; }
fixtures=$(CDPATH= cd -- "$1" && pwd)
umask 077
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/sbin:/usr/bin:/bin:/sbin; export PATH
LC_ALL=C.UTF-8; export LC_ALL
unset LD_LIBRARY_PATH LD_PRELOAD
ulimit -c 0
sysctl kern.boottime > "$work/boot.before"
pkg_info -e lame > "$work/lame-package.txt"
pkg_info -e mpg123 > "$work/mpg123-package.txt"
lame --version > "$work/lame-version.txt"
ldd /usr/pkg/bin/lame > "$work/lame.ldd"
! grep -q 'not found' "$work/lame.ldd"
for encoding in utf8 utf16; do
    timeout -k 5 60 lame --silent --id3v2-only "--id3v2-$encoding" \
        --tt 'Title café 東京' --ta 'Artist café 東京' --tl 'Album café 東京' \
        --tc 'Comment café 東京' --tg Speech --tn 7 --ty 2026 \
        --tv 'TIT3=Subtitle café 東京' -b 192 \
        "$fixtures/tone.wav" "$work/$encoding.mp3" > "$work/$encoding.log" 2>&1
    timeout -k 5 60 mpg123 -q -w "$work/$encoding.wav" "$work/$encoding.mp3" \
        > "$work/$encoding-decode.log" 2>&1
done
result=0
timeout -k 5 60 lame --silent --id3v2-utf8 --tv BROKEN \
    "$fixtures/tone.wav" "$work/invalid.mp3" > "$work/invalid.log" 2>&1 || result=$?
[ "$result" != 0 ] && [ "$result" != 124 ] && [ "$result" != 137 ]
! test -s "$work/invalid.mp3"
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: installed LAME encoded both tag formats; mpg123 decoded; malformed field rejected'
