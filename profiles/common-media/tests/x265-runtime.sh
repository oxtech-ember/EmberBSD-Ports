#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Installed HEVC encoder, scalar/NEON controls.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 VERIFIED_FIXTURES NEW_OUTPUT" >&2; exit 2; }
fixtures=$(CDPATH= cd -- "$1" && pwd)
umask 077
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/sbin:/usr/bin:/bin:/sbin; export PATH
LC_ALL=C; export LC_ALL
unset LD_LIBRARY_PATH LD_PRELOAD
ulimit -c 0
sysctl kern.boottime > "$work/boot.before"
pkg_info -e x265 > "$work/package.txt"
x265 --version > "$work/version.txt" 2>&1
ldd /usr/pkg/bin/x265 > "$work/x265.ldd"
! grep -q 'not found' "$work/x265.ldd"
for mode in neon scalar; do
    set --
    [ "$mode" != scalar ] || set -- --no-asm
    timeout -k 5 120 x265 --no-progress --lossless --pools 1 --frame-threads 1 \
        --input-res 64x64 --fps 24 --frames 4 --input-csp i420 \
        --input "$fixtures/frames.yuv" --output "$work/$mode.hevc" \
        --recon "$work/$mode.yuv" "$@" > "$work/$mode.log" 2>&1
    cmp "$fixtures/frames.yuv" "$work/$mode.yuv"
    grep -q 'encoded 4 frames' "$work/$mode.log"
done
grep -q 'using cpu capabilities:.*NEON' "$work/neon.log"
grep -q 'using cpu capabilities: none' "$work/scalar.log"
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: installed NEON/scalar HEVC encoders reconstructed every source byte'
