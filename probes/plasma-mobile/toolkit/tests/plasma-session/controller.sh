#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Private-bus full session controller.
set -eu
: "${EMBER_PLASMA_OUTPUT:?}" "${EMBER_PLASMA_SESSION_MARKER:?}"
cd "$EMBER_PLASMA_OUTPUT"
trap 'result=$?; printf "%s\n" "$result" > controller.status' 0
query() { /usr/bin/timeout -k 2 5 /usr/pkg/qt6/bin/qdbus "$@"; }
owner()
{
    query org.freedesktop.DBus /org/freedesktop/DBus \
        org.freedesktop.DBus.GetConnectionUnixProcessID "$1"
}
/usr/pkg/bin/kwin_wayland_wrapper --virtual --width 1280 --height 1024 \
    --xwayland --no-lockscreen '/bin/sh ./environment.sh' > compositor.log 2>&1 &
wrapper=$!
printf '%s\n' "$wrapper" > wrapper.pid
deadline=$(($(date +%s) + 100))
while :; do
    kill -0 "$wrapper"
    if [ -f display-env ] && owner org.kde.KWinWrapper > wrapper-owner.pid 2> query-error.log; then break; fi
    [ "$(date +%s)" -lt "$deadline" ] || { echo 'FAIL: KWin display environment deadline' >&2; exit 1; }
    sleep 1
done
[ "$(cat wrapper-owner.pid)" = "$wrapper" ]
{
    read -r WAYLAND_DISPLAY
    read -r DISPLAY
    read -r XAUTHORITY
} < display-env
printf '%s\n' "$WAYLAND_DISPLAY" | grep -Eq '^wayland-[0-9]+$'
printf '%s\n' "$DISPLAY" | grep -Eq '^:[0-9]+$'
case "$XAUTHORITY" in "$TMPDIR"/*) ;; *) echo 'FAIL: Xauthority is outside the private temporary directory' >&2; exit 1 ;; esac
[ -f "$XAUTHORITY" ] && [ ! -L "$XAUTHORITY" ] && [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]
export WAYLAND_DISPLAY DISPLAY XAUTHORITY
/usr/pkg/bin/startplasma-wayland > plasma-session.log 2>&1 &
plasma=$!
printf '%s\n' "$plasma" > startplasma.pid
ready()
{
    query org.kde.ksmserver /KSMServer org.kde.KSMServerInterface.isShuttingDown > ksm-ready.txt || return 1
    grep -qx false ksm-ready.txt || return 1
    query org.kde.ksmserver /KSMServer org.kde.KSMServerInterface.currentSession > ksm-session.txt || return 1
    query org.kde.ActivityManager /ActivityManager/Activities \
        org.kde.ActivityManager.Activities.CurrentActivity > activity.txt || return 1
    grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' activity.txt || return 1
    grep -qx '00000000-0000-0000-0000-000000000000' activity.txt && return 1
    query org.kde.ActivityManager /ActivityManager/Activities \
        org.kde.ActivityManager.Activities.ListActivities > activities.txt || return 1
    grep -Fxq "$(cat activity.txt)" activities.txt || return 1
    query org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.shell > shell.txt || return 1
    grep -qx org.kde.plasma.desktop shell.txt || return 1
    query org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
        "$(cat layout.js)" > layout.txt || return 1
    grep -qx 'PASS: default desktop, panel and six applet models on 1280x1024' layout.txt
}
while ! ready 2> readiness-error.log; do
    kill -0 "$wrapper" && kill -0 "$plasma"
    [ "$(date +%s)" -lt "$deadline" ] || { echo 'FAIL: full Plasma session readiness deadline' >&2; exit 1; }
    sleep 1
done
services='org.kde.KWin org.kde.ksmserver org.kde.ActivityManager org.kde.plasmashell org.kde.kded6'
for service in $services; do owner "$service" > "$service.pid"; done
kwin=$(cat org.kde.KWin.pid)
# Xwayland is KWin's child. Successful ksmserver queries also require its xcb connection.
ps -ax -o pid= -o ppid= -o comm= | awk -v parent="$kwin" \
    '$2 == parent && $3 ~ /(^|\/)Xwayland$/ { print $1 }' > xwayland.pid
[ "$(wc -l < xwayland.pid | tr -d ' ')" = 1 ]
query org.kde.KWin /KWin org.kde.KWin.supportInformation > support-before.txt
/bin/sh ./check-results.sh support support-before.txt
count=0
while [ "$count" -lt 6 ]; do
    sleep 5
    kill -0 "$wrapper" && kill -0 "$plasma" && kill -0 "$(cat xwayland.pid)"
    ready
    for service in $services; do
        [ "$(owner "$service")" = "$(cat "$service.pid")" ]
    done
    count=$((count + 1))
done
query org.kde.KWin /KWin org.kde.KWin.supportInformation > support-after.txt
/bin/sh ./check-results.sh support support-after.txt
shell_pid=$(cat org.kde.plasmashell.pid)
cat bus.log plasma-session.log compositor.log | awk -v prefix="[$shell_pid] " 'index($0, prefix) == 1' > shell-renderer.log
/bin/sh ./check-results.sh renderer shell-renderer.log
# This API performs logout only. It does not request halt or reboot.
query org.kde.Shutdown /Shutdown org.kde.Shutdown.logout > logout.log 2>&1
: > logout.requested
deadline=$(($(date +%s) + 45))
while kill -0 "$wrapper" 2>/dev/null || kill -0 "$plasma" 2>/dev/null; do
    [ "$(date +%s)" -lt "$deadline" ] || { echo 'FAIL: normal Plasma logout deadline' >&2; exit 1; }
    sleep 1
done
wrapper_status=0
wait "$wrapper" || wrapper_status=$?
printf '%s\n' "$wrapper_status" > wrapper.status
plasma_status=0
wait "$plasma" || plasma_status=$?
printf '%s\n' "$plasma_status" > startplasma.status
[ "$wrapper_status" -eq 0 ] && [ "$plasma_status" -eq 0 ]
[ ! -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]
echo 'PASS: full session stayed ready for 30 seconds and completed normal logout'
