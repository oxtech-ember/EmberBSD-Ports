#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run without a desktop or display server.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 ABSOLUTE_BINARY NEW_RESULTS" >&2; exit 2; }
binary=$1 results=$2
case "$binary:$results" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
umask 077
mkdir "$results"
mkdir "$results/cache"
run()
{
    dispatcher=$1
    shift
    /usr/bin/timeout -k 2 20 /usr/bin/env -i \
        PATH=/usr/pkg/bin:/usr/bin:/bin HOME="$HOME" LC_ALL=C.UTF-8 \
        XDG_CACHE_HOME="$results/cache" QT_QPA_PLATFORM=offscreen \
        QT_NO_GLIB="$dispatcher" "$binary" "$@"
}
for dispatcher in '' 1; do
    label=${dispatcher:-default}
    for mode in core gui core-thread gui-thread core-detached gui-detached core-thread-detached gui-thread-detached; do
        set --
        case "$mode" in gui*) set -- "$@" --gui;; esac
        case "$mode" in *-thread*) set -- "$@" --thread-first;; esac
        case "$mode" in *-detached) set -- "$@" --detached-first;; esac
        run "$dispatcher" "$@" > "$results/$label-$mode.log" 2>&1
        grep -q '^PASS: 20 asynchronous child exits ' "$results/$label-$mode.log"
        [ "$(grep -c '^started=' "$results/$label-$mode.log")" = 20 ]
        status=0
        run "$dispatcher" "$@" --missing > "$results/$label-$mode-missing.log" 2>&1 || status=$?
        [ "$status" = 3 ]
        grep -qx 'PASS: missing executable reported FailedToStart' "$results/$label-$mode-missing.log"
    done
done
grep -qx 'dispatcher=QUnixEventDispatcherQPA' "$results/1-gui.log"
grep -qx 'dispatcher=QEventDispatcherUNIX' "$results/1-core.log"
/usr/bin/sha256 "$binary" > "$results/binary.sha256"
echo 'PASS: 320 child exits and sixteen failed launches; Core/GUI, thread and dispatcher variants'
