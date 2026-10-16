#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Called only by run.sh in its private session.
set -eu
: "${EMBER_PLASMA_OUTPUT:?Run this file through run.sh}"
cd "$EMBER_PLASMA_OUTPUT"
plasma_pid=
check_missing_images()
{
    for missing_image in missing-output-*.png; do
        if [ -e "$missing_image" ] || [ -L "$missing_image" ]; then
            echo "FAIL: an unknown output created an image: $missing_image" >&2
            return 1
        fi
    done
}
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
    check_missing_images || result=1
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
    if query org.kde.plasmashell /PlasmaShell org.freedesktop.DBus.Properties.Get \
            org.kde.PlasmaShell shell \
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
# A bare Folder View can produce a valid fully transparent PNG. Add visible
# content to this private test containment before checking decoded pixels.
while :; do
    remaining=$((deadline - $(date +%s)))
    [ "$remaining" -gt 0 ] || {
        echo 'FAIL: capture widget did not become ready before the startup deadline' >&2
        exit 1
    }
    kill -0 "$plasma_pid" 2>/dev/null || exit 1
    widget_timeout=$remaining
    [ "$widget_timeout" -le 5 ] || widget_timeout=5
    if /usr/bin/timeout -k 2 "$widget_timeout" /usr/pkg/qt6/bin/qdbus \
        org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
        "$(cat capture-layout.js)" > capture-layout.txt 2> capture-layout-error.log &&
        grep -qx 'PASS: capture widget created' capture-layout.txt; then
        break
    fi
    sleep 1
done
# This internal API must reject an unknown connector; it must not save a file.
# Cold D-Bus introspection can time out before the method is called. Retry only
# that timeout, within the original startup deadline. Do not accept it as proof.
missing_attempt=0
while :; do
    check_missing_images
    remaining=$((deadline - $(date +%s)))
    [ "$remaining" -gt 0 ] || {
        echo 'FAIL: unknown-output rejection did not arrive before the startup deadline' >&2
        exit 1
    }
    kill -0 "$plasma_pid" 2>/dev/null || exit 1
    missing_timeout=$remaining
    [ "$missing_timeout" -le 5 ] || missing_timeout=5
    missing_attempt=$((missing_attempt + 1))
    missing_prefix="missing-output-$missing_attempt"
    printf '%s\n' "$missing_timeout" > "$missing_prefix.timeout"
    missing_status=0
    /usr/bin/timeout -k 2 "$missing_timeout" /usr/pkg/qt6/bin/qdbus \
        org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.grabContainmentImage \
        Ember-Missing-Output 320 256 "$PWD/$missing_prefix.png" \
        > "$missing_prefix.log" 2>&1 || missing_status=$?
    printf '%s\n' "$missing_status" > "$missing_prefix.status"
    check_missing_images
    case "$missing_status" in
    0)
        echo 'FAIL: an unknown output was accepted' >&2
        exit 1 ;;
    124)
        sleep 1 ;;
    2)
        # Workspace sends InvalidArgs. QtTools qdbus prints these two lines
        # and returns 2 for the error reply. Other errors are not this control.
        printf '%s\n' 'Error: org.freedesktop.DBus.Error.InvalidArgs' \
            'Unknown screen name' | cmp -s - "$missing_prefix.log" || {
            echo 'FAIL: unexpected unknown-output error reply' >&2
            exit 1
        }
        cp "$missing_prefix.log" missing-output.log
        break ;;
    *)
        echo "FAIL: unexpected unknown-output query status: $missing_status" >&2
        exit 1 ;;
    esac
done
# Layout models can precede a visible Quick item. Keep capture retries inside
# the original startup deadline. Separate paths also isolate late D-Bus replies.
capture_attempt=0
capture_status=not-started
capture_check_status=not-started
while :; do
    remaining=$((deadline - $(date +%s)))
    [ "$remaining" -gt 0 ] || {
        echo "FAIL: capture did not become ready before the startup deadline; attempts=$capture_attempt, request=$capture_status, check=$capture_check_status" >&2
        exit 1
    }
    kill -0 "$plasma_pid" 2>/dev/null || {
        echo 'FAIL: plasmashell exited before capture' >&2
        exit 1
    }
    capture_timeout=$remaining
    [ "$capture_timeout" -le 15 ] || capture_timeout=15
    capture_attempt=$((capture_attempt + 1))
    capture_prefix="capture-$capture_attempt"
    printf '%s\n' "$capture_timeout" > "$capture_prefix.timeout"
    capture_status=0
    /usr/bin/timeout -k 2 "$capture_timeout" /usr/pkg/qt6/bin/qdbus \
        org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.grabContainmentImage \
        Virtual-0 320 256 "$PWD/$capture_prefix.png" \
        > "$capture_prefix.txt" 2> "$capture_prefix-error.log" || capture_status=$?
    printf '%s\n' "$capture_status" > "$capture_prefix.status"
    capture_check_status=1
    if [ "$capture_status" -eq 0 ] && grep -qx true "$capture_prefix.txt"; then
        capture_check_status=0
        /bin/sh ./check-results.sh png "$capture_prefix.png" \
            > "$capture_prefix-check.log" 2>&1 || capture_check_status=$?
        if [ "$capture_check_status" -eq 0 ]; then
            ./capture-pixels "$capture_prefix.png" >> "$capture_prefix-check.log" 2>&1 || capture_check_status=$?
        fi
    else
        echo 'FAIL: capture request did not return true successfully' > "$capture_prefix-check.log"
    fi
    printf '%s\n' "$capture_check_status" > "$capture_prefix-check.status"
    if [ "$capture_status" -eq 0 ] && [ "$capture_check_status" -eq 0 ]; then
        cp "$capture_prefix.png" desktop.png
        cp "$capture_prefix.txt" capture.txt
        cp "$capture_prefix-error.log" capture-error.log
        break
    fi
    sleep 1
done
check_missing_images
# Reject a software fallback in the shell itself, not only in the compositor.
/bin/sh ./check-results.sh renderer plasmashell.log
count=0
while [ "$count" -lt 6 ]; do
    sleep 5
    check_missing_images
    kill -0 "$plasma_pid"
    query org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
        "$(cat layout.js)" > "layout-$count.txt"
    grep -qx 'PASS: default desktop, panel and six applet models on 1280x1024' "layout-$count.txt"
    count=$((count + 1))
done
/bin/sh ./check-results.sh renderer plasmashell.log
query org.kde.KWin /KWin org.kde.KWin.supportInformation > supportinformation-after.txt
/bin/sh ./check-results.sh support supportinformation-after.txt
check_missing_images
echo 'PASS: Plasma Desktop virtual shell; 30 seconds of layout liveness'
