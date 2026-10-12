#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual installed module protocol regression.
set -eu
[ "$#" = 2 ] || { echo 'Usage: speech-dummy-runtime.sh MODULE NEW_RESULTS' >&2; exit 2; }
module=$(realpath "$1")
mkdir "$2"
result=$(CDPATH= cd -- "$2" && pwd)
mkdir "$result/bin"
trap 'rm -rf "$result/bin"' EXIT
trap 'exit 1' HUP INT TERM
# Dummy's fallback child must never open a real audio device in this check.
printf '#!/bin/sh\nexit 0\n' > "$result/bin/play"
chmod +x "$result/bin/play"
PATH=$result/bin:$PATH; export PATH
ulimit -c 0
for iteration in 1 2 3 4 5 6 7 8; do
    for mode in immediate delayed speaking; do
        {
            printf 'INIT\n'
            case "$mode" in
                delayed) sleep 0.05 ;;
                speaking) printf 'SPEAK\nEmberBSD test.\n.\n' ;;
            esac
            printf 'QUIT\n'
        } | timeout -k 2 5 "$module" > "$result/$mode-$iteration.log" 2>&1
        grep -qx '299 OK LOADED SUCCESSFULLY' "$result/$mode-$iteration.log"
        grep -qx '210 OK QUIT' "$result/$mode-$iteration.log"
    done
done
echo 'PASS: 24 real module INIT/QUIT cycles, including delayed startup and queued speech'
