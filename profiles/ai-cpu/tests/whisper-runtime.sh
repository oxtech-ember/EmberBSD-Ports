#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real tiny-model file transcription contracts.
set -eu
[ "$#" = 4 ] || { echo 'Usage: whisper-runtime.sh CLI MODEL JFK_WAV NEW_OUTPUT' >&2; exit 2; }
cli=$1 model=$2 wav=$3 out=$4
for path do case "$path" in /*) ;; *) exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
[ -x "$cli" ] && [ -f "$model" ] && [ -f "$wav" ] || exit 2
export LC_ALL=C
hash() {
    if command -v sha256 >/dev/null 2>&1; then sha256 -q "$1";
    else sha256sum "$1" | awk '{ print $1 }'; fi
}
[ "$(hash "$model")" = be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21 ] || exit 1
[ "$(hash "$wav")" = 59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e ] || exit 1
mkdir "$out"
ulimit -c 0
transcribe() {
    "$cli" -m "$model" -f "$wav" -l en -t 2 -p 1 -bo 1 -bs 1 -nf -ng "$@"
}
if [ "$(uname -s)" = NetBSD ]; then
    /usr/bin/time -l "$cli" -m "$model" -f "$wav" -l en -t 2 -p 1 \
        -bo 1 -bs 1 -nf -ng -otxt -ojf -of "$out/transcript" \
        > "$out/transcript.stdout" 2> "$out/transcript.log"
else
    transcribe -otxt -ojf -of "$out/transcript" > "$out/transcript.stdout" 2> "$out/transcript.log"
fi
tr '[:upper:]' '[:lower:]' < "$out/transcript.txt" | tr -cs 'a-z' ' ' | \
    sed 's/^ *//; s/ *$//' > "$out/normalized.txt"
printf '%s' 'and so my fellow americans ask not what your country can do for you ask what you can do for your country' > "$out/expected.txt"
# Normalization keeps word order; the reference is independent of engine output.
[ "$(cat "$out/normalized.txt")" = "$(cat "$out/expected.txt")" ] || exit 1
expect() {
    wanted=$1 name=$2; shift 2
    status=0
    "$@" > "$out/$name.stdout" 2> "$out/$name.log" || status=$?
    printf '%s\n' "$status" > "$out/$name.status"
    [ "$status" = "$wanted" ] || { echo "Unexpected $name status: $status" >&2; exit 1; }
}
printf 'not a Whisper model\n' > "$out/invalid.bin"
expect 3 invalid-model "$cli" -m "$out/invalid.bin" -f "$wav" -ng
grep -q 'invalid model data' "$out/invalid-model.log"
expect 2 missing-audio "$cli" -m "$model" -f "$out/missing.wav" -ng
grep -q 'input file not found' "$out/missing-audio.log"
printf RIFF > "$out/broken.wav"
expect 11 broken-audio "$cli" -m "$model" -f "$out/broken.wav" -ng
grep -q 'failed to read audio' "$out/broken-audio.log"
expect 11 output-open transcribe -otxt -of "$out/no-directory/transcript"
grep -q 'failed to open' "$out/output-open.log"
[ -c /dev/full ] || { echo 'The output-write regression requires /dev/full.' >&2; exit 1; }
ln -s /dev/full "$out/full.txt"
expect 11 output-write transcribe -otxt -ojf -of "$out/full"
grep -q 'failed to write' "$out/output-write.log"
[ -s "$out/full.json" ] || exit 1
expect 11 wts-font transcribe -owts -fp "$out/missing-font.ttf" -of "$out/font"
grep -q 'font not found' "$out/wts-font.log"
expect 11 input-indices "$cli" -m "$model" -f "$out/missing.wav" -f "$wav" \
    -of "$out/missing-output" -of "$out/valid-output" -l en -t 2 -p 1 -bo 1 -bs 1 -nf -ng -otxt
[ ! -e "$out/missing-output.txt" ] && [ -s "$out/valid-output.txt" ] || exit 1
cmp "$out/transcript.txt" "$out/valid-output.txt"
echo 'PASS: exact JFK words, malformed inputs, output failures and batch output identity'
