#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Selected real codec tests and damaged inputs.
set -eu
[ "$#" = 2 ] || { echo 'Usage: run-tests.sh TESTS NEW_RESULTS' >&2; exit 2; }
tests=$1 out=$2
for path do case "$path" in /*) ;; *) exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
mkdir -p "$out"
cd "$out"
run()
{
    expected=$1 name=$2; shift 2
    status=0
    if [ "${CODECS_MEMCHECK:-0}" = 1 ]; then
        valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
            --errors-for-leak-kinds=definite,indirect,possible --track-origins=yes \
            --error-exitcode=99 --log-file="$out/$name.memcheck.log" \
            "$@" > "$out/$name.log" 2>&1 || status=$?
        grep -F 'ERROR SUMMARY: 0 errors' "$out/$name.memcheck.log" >/dev/null
    else
        "$@" > "$out/$name.log" 2>&1 || status=$?
    fi
    printf '%s %s %s\n' "$name" "$expected" "$status" >> "$out/statuses.txt"
    [ "$status" = "$expected" ] || { cat "$out/$name.log" >&2; exit 1; }
}
run 0 png-roundtrip "$tests/bin/pngtest" "$tests/fixtures/pngtest.png" "$out/roundtrip.png"
run 0 png-standard "$tests/bin/pngvalid" --standard
run 0 jpeg-roundtrip "$tests/bin/tjunittest"
run 0 jpeg-yuv "$tests/bin/tjunittest" -yuv
run 0 jpeg-lossless16 "$tests/bin/tjunittest" -lossless -precision 16
run 0 jpeg-encode "$tests/bin/cjpeg" -quality 95 -outfile "$out/encoded.jpg" "$tests/fixtures/testorig.ppm"
run 0 jpeg-decode "$tests/bin/djpeg" -outfile "$out/decoded.ppm" "$out/encoded.jpg"
: > "$out/empty"
head -c 24 "$tests/fixtures/pngtest.png" > "$out/truncated.png"
head -c 24 "$tests/fixtures/testorig.jpg" > "$out/truncated.jpg"
run 1 png-empty "$tests/bin/pngtest" "$out/empty" "$out/empty-output.png"
run 1 png-truncated "$tests/bin/pngtest" "$out/truncated.png" "$out/truncated-output.png"
run 1 jpeg-empty "$tests/bin/djpeg" -outfile "$out/empty-output.ppm" "$out/empty"
run 1 jpeg-truncated "$tests/bin/djpeg" -outfile "$out/truncated-output.ppm" "$out/truncated.jpg"
echo 'PASS: selected PNG/JPEG encode, decode, YUV, 16-bit lossless and damaged-input checks'
