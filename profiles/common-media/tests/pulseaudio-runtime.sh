#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Private Unix socket and null sink; no audio device.
set -eu
[ "$#" = 2 ] || { echo 'Usage: pulseaudio-runtime.sh PCM_FIXTURE NEW_RESULTS' >&2; exit 2; }
fixture=$(realpath "$1")
mkdir "$2"
result=$(CDPATH= cd -- "$2" && pwd)
umask 077
mkdir -p "$result/scratch/home" "$result/scratch/runtime"
server= recorder=
cleanup() {
    if [ -n "$recorder" ]; then kill "$recorder" 2>/dev/null || :; wait "$recorder" 2>/dev/null || :; fi
    if [ -n "$server" ]; then kill "$server" 2>/dev/null || :; wait "$server" 2>/dev/null || :; fi
    rm -rf "$result/scratch"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
ulimit -c 0
unset LD_LIBRARY_PATH
export HOME=$result/scratch/home
export XDG_CONFIG_HOME=$HOME/.config
export XDG_RUNTIME_DIR=$result/scratch/runtime
export PULSE_RUNTIME_PATH=$XDG_RUNTIME_DIR
export PULSE_STATE_PATH=$HOME/state
export PULSE_SERVER=unix:$XDG_RUNTIME_DIR/pulse.sock
pulseaudio --daemonize=no --use-pid-file=no --exit-idle-time=-1 \
    --disable-shm=yes --log-target=stderr --log-level=debug -n \
    --load="module-native-protocol-unix socket=$XDG_RUNTIME_DIR/pulse.sock auth-anonymous=1" \
    --load='module-null-sink sink_name=ember_test rate=48000 channels=1' \
    > "$result/server.log" 2>&1 &
server=$!
i=0
until [ -S "$XDG_RUNTIME_DIR/pulse.sock" ]; do
    if ! kill -0 "$server" 2>/dev/null; then
        code=0
        wait "$server" || code=$?
        printf '%s\n' "$code" > "$result/server-exit.txt"
        server=
        exit 1
    fi
    i=$((i + 1)); [ "$i" -le 50 ]; sleep 0.1
done
timeout -k 2 10 pactl info > "$result/info.txt"
timeout -k 2 10 pactl list short sinks > "$result/sinks.txt"
grep 'ember_test' "$result/sinks.txt" >/dev/null
pactl set-sink-volume ember_test 100%
pactl set-source-volume ember_test.monitor 100%
parec --device=ember_test.monitor --raw --format=s16le --rate=48000 \
    --channels=1 --latency-msec=20 > "$result/capture.s16le" 2> "$result/record.log" &
recorder=$!
i=0
while :; do
    kill -0 "$recorder"
    pactl list short source-outputs > "$result/source-outputs.txt"
    [ ! -s "$result/source-outputs.txt" ] || break
    i=$((i + 1)); [ "$i" -le 50 ]; sleep 0.1
done
# A registered recording stream can still be discarding its startup latency.
# Wait for actual captured silence before sending the bounded test payload.
i=0
until [ "$(wc -c < "$result/capture.s16le" | tr -d ' ')" -ge 4096 ]; do
    kill -0 "$recorder"
    i=$((i + 1)); [ "$i" -le 50 ]; sleep 0.1
done
timeout -k 2 15 paplay --device=ember_test --raw --format=s16le --rate=48000 \
    --channels=1 "$fixture" > "$result/play.log" 2>&1
sleep 0.2
kill "$recorder"
wait "$recorder" || :
recorder=
[ -s "$result/capture.s16le" ]
if timeout -k 2 10 paplay "$result/missing-input.wav" > "$result/missing.log" 2>&1; then
    echo 'Missing input unexpectedly played' >&2; exit 1
fi
pactl list short sink-inputs > "$result/remaining-streams.txt"
[ ! -s "$result/remaining-streams.txt" ]
kill "$server"
wait "$server"
server=
echo 'PASS: private PulseAudio server, null-sink playback/capture, missing-file refusal and shutdown'
