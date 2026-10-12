#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Isolated speech service; no hardware audio.
set -eu
[ "$#" = 2 ] || { echo 'Usage: run.sh QT_SPEECH_BINARY NEW_RESULTS' >&2; exit 2; }
binary=$(realpath "$1")
mkdir "$2"
result=$(CDPATH= cd -- "$2" && pwd)
umask 077
mkdir -p "$result/scratch/home" "$result/scratch/runtime" "$result/scratch/config/modules" "$result/scratch/log"
server=
stop_server() {
    [ -n "$server" ] || return 0
    children=$(pgrep -P "$server" || :)
    kill "$server" 2>/dev/null || :
    i=0
    while kill -0 "$server" 2>/dev/null && [ "$i" -lt 50 ]; do
        i=$((i+1)); sleep 0.1
    done
    forced=0
    if kill -0 "$server" 2>/dev/null; then
        forced=1
        for child in $children; do kill -KILL "$child" 2>/dev/null || :; done
        kill -KILL "$server" 2>/dev/null || :
    fi
    status=0
    wait "$server" || status=$?
    server=
    [ "$forced" = 0 ] && [ "$status" = 0 ]
}
cleanup() {
    status=$?
    trap - EXIT
    stop_server || status=1
    cp -R "$result/scratch/log" "$result/service-logs"
    rm -rf "$result/scratch"
    exit "$status"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
ulimit -c 0
unset LD_LIBRARY_PATH
export HOME=$result/scratch/home XDG_RUNTIME_DIR=$result/scratch/runtime LC_ALL=C.UTF-8
export XDG_CONFIG_HOME=$HOME/.config
export SPEECHD_ADDRESS=unix_socket:$XDG_RUNTIME_DIR/speech.sock
printf 'default_driver=null\n' > "$HOME/.libao"
cp /usr/pkg/share/examples/speech-dispatcher/modules/espeak-ng.conf "$result/scratch/config/modules/"
cat > "$result/scratch/config/speechd.conf" <<'EOF'
CommunicationMethod "unix_socket"
AddModule "espeak-ng" "sd_espeak-ng" "espeak-ng.conf"
DefaultModule "espeak-ng"
AudioOutputMethod "libao"
DisableAutoSpawn
EOF
speech-dispatcher --run-single --config-dir="$result/scratch/config" \
    --socket-path="$XDG_RUNTIME_DIR/speech.sock" --pid-file="$result/scratch/speech.pid" \
    --log-dir="$result/scratch/log" --log-level=4 --timeout=0 > "$result/server.log" 2>&1 &
server=$!
i=0
until [ -S "$XDG_RUNTIME_DIR/speech.sock" ]; do
    kill -0 "$server"
    i=$((i+1)); [ "$i" -le 50 ]; sleep 0.1
done
timeout -k 2 10 spd-say --list-output-modules > "$result/modules.txt"
grep 'espeak-ng' "$result/modules.txt" > /dev/null
timeout -k 2 10 spd-say --list-synthesis-voices > "$result/voices.txt"
grep 'English' "$result/voices.txt" > /dev/null
for iteration in 1 2; do
    timeout -k 3 20 "$binary" flite > "$result/flite-$iteration.log" 2>&1
    timeout -k 3 20 "$binary" speechd > "$result/speechd-$iteration.log" 2>&1
done
timeout -k 3 20 "$binary" ember-missing-engine > "$result/missing-engine.log" 2>&1
stop_server
echo 'PASS: private speech-dispatcher/eSpeak service, two Qt flite/PCM and speechd processes, missing engine and shutdown'
