#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Bounded installed software-player acceptance.
set -eu
[ "$#" = 4 ] || { echo 'Usage: run.sh BINARY MOVIE YUV NEW_RESULTS' >&2; exit 2; }
binary=$(realpath "$1") movie=$(realpath "$2") yuv=$(realpath "$3")
mkdir "$4"
result=$(CDPATH= cd -- "$4" && pwd)
umask 077
mkdir "$result/runtime"
trap 'rm -rf "$result/runtime"' EXIT
trap 'exit 1' HUP INT TERM
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/sbin:/usr/bin:/bin:/sbin; export PATH
LC_ALL=C.UTF-8; export LC_ALL
unset LD_LIBRARY_PATH LD_PRELOAD
ulimit -c 0
export XDG_RUNTIME_DIR=$result/runtime QT_QPA_PLATFORM=offscreen
export QT_MEDIA_BACKEND=ffmpeg QT_FFMPEG_DECODING_HW_DEVICE_TYPES=,
sysctl kern.boottime > "$result/boot.before"
for attempt in first restart; do
    timeout -k 3 25 "$binary" "$movie" "$yuv" normal > "$result/$attempt.log" 2>&1
    grep -F 'PASS: end of media and exact decoded pixels; frames=4 Qt=6.12.0' "$result/$attempt.log" >/dev/null
done
code=0
timeout -k 3 25 "$binary" "$movie" "$yuv" wrong-pixel > "$result/wrong-pixel.log" 2>&1 || code=$?
[ "$code" = 3 ]
grep -F 'FAIL: decoded pixels differ' "$result/wrong-pixel.log" >/dev/null
timeout -k 3 25 "$binary" "$result/missing.mkv" "$yuv" missing > "$result/missing.log" 2>&1
grep -F 'PASS: missing media refused; frames=0' "$result/missing.log" >/dev/null
sed -n 's/^loaded=\(\/usr\/pkg\/.*\)$/\1/p' "$result/first.log" | sort -u > "$result/libraries.txt"
while read -r library; do printf '%s  %s\n' "$(sha256 -q "$library")" "$library"; done < "$result/libraries.txt" > "$result/libraries.sha256"
sysctl kern.boottime > "$result/boot.after"
cmp "$result/boot.before" "$result/boot.after"
echo 'PASS: exact Qt player pixels, process restart, wrong-pixel and missing-input controls; unchanged boot'
