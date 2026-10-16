#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Private-bus full session controller.
set -eu
: "${EMBER_PLASMA_OUTPUT:?}" "${EMBER_PLASMA_SESSION_MARKER:?}"
cd "$EMBER_PLASMA_OUTPUT"
phase=display-environment
trap 'result=$?; printf "%s\n" "$result" > controller.status; if [ "$result" -ne 0 ]; then echo "FAIL: controller phase=$phase status=$result" >&2; fi' 0
query()
{
    query_started=$(date +%s)
    query_status=0
    /usr/bin/timeout -k 2 5 /usr/pkg/qt6/bin/qdbus "$@" || query_status=$?
    query_finished=$(date +%s)
    # Record the call identity, not its payload or the process environment.
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$query_started" "$query_finished" \
        "$phase" "$query_status" "$1" "$2" "$3" >> queries.tsv
    if [ "$query_status" -ne 0 ]; then
        echo "FAIL: query phase=$phase status=$query_status service=$1 object=$2 method=$3" >&2
    fi
    return "$query_status"
}
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
# KWin 6.8 creates xauth_XXXXXX in QStandardPaths::RuntimeLocation.
# Accept a direct file in this runner's private runtime directory only.
case "$XDG_RUNTIME_DIR" in "$EMBER_PLASMA_OUTPUT/runtime") ;;
    *) echo 'FAIL: Xauthority runtime directory does not belong to this session' >&2; exit 1 ;; esac
uid=$(/usr/bin/id -u)
for directory in "$EMBER_PLASMA_OUTPUT" "$XDG_RUNTIME_DIR"; do
    if [ -L "$directory" ] || [ ! -d "$directory" ] ||
        [ "$(/usr/bin/stat -f '%u:%p' "$directory" 2>/dev/null)" != "$uid:40700" ]; then
        echo 'FAIL: unsafe private Xauthority directory' >&2; exit 1
    fi
done
case "$XAUTHORITY" in "$XDG_RUNTIME_DIR"/*) authority_name=${XAUTHORITY#"$XDG_RUNTIME_DIR"/} ;;
    *) echo 'FAIL: Xauthority is outside the private runtime directory' >&2; exit 1 ;; esac
case "$authority_name" in ''|.|..|*/*)
    echo 'FAIL: Xauthority is not a direct runtime file' >&2; exit 1 ;; esac
if [ -L "$XAUTHORITY" ] || [ ! -f "$XAUTHORITY" ] ||
    [ "$(/usr/bin/stat -f '%u:%p' "$XAUTHORITY" 2>/dev/null)" != "$uid:100600" ]; then
    echo 'FAIL: unsafe private Xauthority file' >&2; exit 1
fi
[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]
export WAYLAND_DISPLAY DISPLAY XAUTHORITY
/usr/pkg/bin/startplasma-wayland > plasma-session.log 2>&1 &
plasma=$!
printf '%s\n' "$plasma" > startplasma.pid
ready()
{
    query org.kde.ksmserver /KSMServer org.kde.KSMServerInterface.isShuttingDown > ksm-ready.txt || return $?
    grep -qx false ksm-ready.txt || return $?
    query org.kde.ksmserver /KSMServer org.kde.KSMServerInterface.currentSession > ksm-session.txt || return $?
    query org.kde.ActivityManager /ActivityManager/Activities \
        org.kde.ActivityManager.Activities.CurrentActivity > activity.txt || return $?
    grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' activity.txt || return $?
    grep -qx '00000000-0000-0000-0000-000000000000' activity.txt && return 1
    query org.kde.ActivityManager /ActivityManager/Activities \
        org.kde.ActivityManager.Activities.ListActivities > activities.txt || return $?
    grep -Fxq "$(cat activity.txt)" activities.txt || return $?
    query org.kde.plasmashell /PlasmaShell org.freedesktop.DBus.Properties.Get \
        org.kde.PlasmaShell shell > shell.txt || return $?
    grep -qx org.kde.plasma.desktop shell.txt || return $?
    query org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
        "$(cat layout.js)" > layout.txt || return $?
    grep -qx 'PASS: default desktop, panel and six applet models on 1280x1024' layout.txt
}
phase=startup-readiness
while ! ready 2> readiness-error.log; do
    kill -0 "$wrapper" && kill -0 "$plasma"
    [ "$(date +%s)" -lt "$deadline" ] || { echo 'FAIL: full Plasma session readiness deadline' >&2; exit 1; }
    sleep 1
done
phase=service-owners
services='org.kde.KWin org.kde.ksmserver org.kde.ActivityManager org.kde.plasmashell org.kde.kded6'
for service in $services; do owner "$service" > "$service.pid"; done
kwin=$(cat org.kde.KWin.pid)
# Xwayland is KWin's child. Successful ksmserver queries also require its xcb connection.
ps -ax -o pid= -o ppid= -o comm= | awk -v parent="$kwin" \
    '$2 == parent && $3 ~ /(^|\/)Xwayland$/ { print $1 }' > xwayland.pid
[ "$(wc -l < xwayland.pid | tr -d ' ')" = 1 ]
phase=support-before
query org.kde.KWin /KWin org.kde.KWin.supportInformation > support-before.txt
/bin/sh ./check-results.sh support support-before.txt
count=0
while [ "$count" -lt 6 ]; do
    phase=liveness-$((count + 1))
    sleep 5
    kill -0 "$wrapper" && kill -0 "$plasma" && kill -0 "$(cat xwayland.pid)"
    ready
    for service in $services; do
        [ "$(owner "$service")" = "$(cat "$service.pid")" ]
    done
    count=$((count + 1))
done
phase=support-after
query org.kde.KWin /KWin org.kde.KWin.supportInformation > support-after.txt
/bin/sh ./check-results.sh support support-after.txt
shell_pid=$(cat org.kde.plasmashell.pid)
cat bus.log plasma-session.log compositor.log | awk -v prefix="[$shell_pid] " 'index($0, prefix) == 1' > shell-renderer.log
/bin/sh ./check-results.sh renderer shell-renderer.log
# This API performs logout only. It does not request halt or reboot.
phase=logout
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
