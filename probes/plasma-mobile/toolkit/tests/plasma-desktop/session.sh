#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Called only by run.sh in its private session.
set -eu
: "${EMBER_PLASMA_OUTPUT:?Run this file through run.sh}"
cd "$EMBER_PLASMA_OUTPUT"
plasma_pid=
cleanup()
{
    result=$?
    trap - 0 HUP INT TERM
    if [ -n "$plasma_pid" ]; then
        kill -TERM "$plasma_pid" 2>/dev/null || :
        tries=0
        while kill -0 "$plasma_pid" 2>/dev/null && [ "$tries" -lt 5 ]; do
            sleep 1
            tries=$((tries + 1))
        done
        if kill -0 "$plasma_pid" 2>/dev/null; then
            echo 'FAIL: plasmashell required SIGKILL' >&2
            kill -KILL "$plasma_pid" 2>/dev/null || :
            result=1
        fi
        shell_status=0
        wait "$plasma_pid" || shell_status=$?
        printf '%s\n' "$shell_status" > plasmashell.status
        [ "$shell_status" -eq 0 ] || result=1
    fi
    printf '%s\n' "$result" > client.status
    exit "$result"
}
trap cleanup 0
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
export WAYLAND_DISPLAY=wayland-0
[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]
query()
{
    /usr/bin/timeout -k 2 5 /usr/pkg/qt6/bin/qdbus "$@"
}
query org.kde.KWin /KWin org.kde.KWin.supportInformation > supportinformation.txt
/bin/sh ./check-results.sh support supportinformation.txt
/usr/pkg/bin/plasmashell --no-respawn --shell-plugin org.kde.plasma.desktop \
    > plasmashell.log 2>&1 &
plasma_pid=$!
printf '%s\n' "$plasma_pid" > plasmashell.pid
# Use elapsed time as well as the outer timeout. A blocked query is bounded.
deadline=$(($(date +%s) + 90))
while :; do
    kill -0 "$plasma_pid" 2>/dev/null || {
        echo 'FAIL: plasmashell exited during startup' >&2
        exit 1
    }
    if query org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.shell \
            > shell.txt 2> query-error.log &&
        grep -qx 'org.kde.plasma.desktop' shell.txt &&
        query org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
            "$(cat layout.js)" > layout.txt 2> query-error.log &&
        grep -qx 'PASS: default desktop, panel and six applet models on 1280x1024' layout.txt; then
        break
    fi
    [ "$(date +%s)" -lt "$deadline" ] || {
        echo 'FAIL: the default Plasma layout did not become ready' >&2
        exit 1
    }
    sleep 1
done
# This internal API must reject an unknown connector; it must not save a file.
if query org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.grabContainmentImage \
        Ember-Missing-Output 320 256 "$PWD/missing.png" > missing-output.log 2>&1; then
    echo 'FAIL: an unknown output was accepted' >&2
    exit 1
fi
grep -q 'Unknown screen name' missing-output.log
[ ! -e missing.png ]
/usr/bin/timeout -k 2 15 /usr/pkg/qt6/bin/qdbus \
    org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.grabContainmentImage \
    Virtual-0 320 256 "$PWD/desktop.png" > capture.txt 2> capture-error.log
grep -qx true capture.txt
/bin/sh ./check-results.sh png desktop.png
# Reject a software fallback in the shell itself, not only in the compositor.
/bin/sh ./check-results.sh renderer plasmashell.log
count=0
while [ "$count" -lt 6 ]; do
    sleep 5
    kill -0 "$plasma_pid"
    query org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
        "$(cat layout.js)" > "layout-$count.txt"
    grep -qx 'PASS: default desktop, panel and six applet models on 1280x1024' "layout-$count.txt"
    count=$((count + 1))
done
/bin/sh ./check-results.sh renderer plasmashell.log
query org.kde.KWin /KWin org.kde.KWin.supportInformation > supportinformation-after.txt
/bin/sh ./check-results.sh support supportinformation-after.txt
echo 'PASS: Plasma Desktop virtual shell; 30 seconds of layout liveness'
