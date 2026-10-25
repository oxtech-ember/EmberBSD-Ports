#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Private-bus full session controller.
set -eu
: "${EMBER_PLASMA_OUTPUT:?}" "${EMBER_PLASMA_SESSION_MARKER:?}"
profile=${EMBER_PLASMA_RENDERER_PROFILE-v3d}
case "$profile" in v3d|powervr-zink|radeonsi) ;; *) exit 2 ;; esac
backend=${EMBER_PLASMA_BACKEND-virtual}
expected_drm_output=${EMBER_PLASMA_EXPECTED_DRM_OUTPUT-HDMI-A-1}
expected_refresh=${EMBER_PLASMA_EXPECTED_REFRESH_MILLIHZ-60000}
# Only this enum selects the launch arguments and layout assertion values.
case "$backend" in
virtual)
    [ "$expected_refresh" = 60000 ] || exit 2
    width=1280; height=1024; output_name=Virtual-0
    backend_name=KWin::VirtualBackend; refresh_millihz=60000 ;;
drm)
    case "$expected_drm_output" in ''|*[!A-Za-z0-9_.-]*) exit 2 ;; esac
    [ "${#expected_drm_output}" -le 32 ] || exit 2
    case "$expected_refresh" in ''|0*|*[!0-9]*) exit 2 ;; esac
    [ "${#expected_refresh}" -le 7 ] || exit 2
    width=1920; height=1080; output_name=$expected_drm_output
    backend_name=DRM; refresh_millihz=$expected_refresh ;;
*) exit 2 ;;
esac
cd "$EMBER_PLASMA_OUTPUT"
printf '%s %s %s %s %s\n' "$backend" "$width" "$height" "$output_name" "$refresh_millihz" > output-policy.txt
phase=display-environment
trap 'result=$?; printf "%s\n" "$result" > controller.status; if [ "$result" -ne 0 ]; then echo "FAIL: controller phase=$phase status=$result" >&2; fi' 0
stamp()
{
    /usr/pkg/bin/perl -MTime::HiRes=clock_gettime,CLOCK_MONOTONIC \
        -e 'printf "%s\t%.6f\n", $ARGV[0], clock_gettime(CLOCK_MONOTONIC)' "$1" >> phases.tsv
}
monotonic_seconds()
{
    /usr/pkg/bin/perl -MTime::HiRes=clock_gettime,CLOCK_MONOTONIC \
        -e 'printf "%d\n", clock_gettime(CLOCK_MONOTONIC)'
}
stamp controller-start
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
render_health()
{
    for render_log in bus.log compositor.log plasma-session.log; do
        if [ -L "$render_log" ] || [ ! -f "$render_log" ] || [ ! -r "$render_log" ]; then
            echo "FAIL: render health phase=$phase unreadable regular log=$render_log" >&2
            return 1
        fi
        render_status=0
        # stderr is also captured in bus.log. Stop after the first match so
        # this scan cannot read its own error output back from that log.
        awk 'index($0, "MESA: error:") { printf "%s:%d:%s\n", FILENAME, FNR, $0; exit 1 }' \
            "$render_log" >&2 || render_status=$?
        if [ "$render_status" -ne 0 ]; then
            echo "FAIL: render health phase=$phase log=$render_log status=$render_status" >&2
            return 1
        fi
    done
}
backend_check()
{
    # Match the KWin 6.8 backend and current output fields, not unrelated names.
    if ! awk -v expected_backend="$backend_name" -v expected_name="$output_name" \
        -v expected_geometry="0,0,${width}x${height}" -v expected_refresh_millihz="$refresh_millihz" '
        $0 == "LogicalOutput backend" { section="backend"; next }
        section == "backend" && /^Name: / { names++; bad += ($0 != "Name: " expected_backend); next }
        section == "backend" && $0 == "" { section="" }
        $0 == "Screens" { section="screens"; next }
        $0 == "Compositing" { section="" }
        section == "screens" && /^Number of Screens: / { counts++; bad += ($0 != "Number of Screens: 1") }
        section == "screens" && /^Screen [0-9]+:$/ { screens++; bad += ($0 != "Screen 0:") }
        section == "screens" && /^Name: / { outputs++; bad += ($0 != "Name: " expected_name) }
        section == "screens" && /^Enabled: / { enabled++; bad += ($0 != "Enabled: 1") }
        section == "screens" && /^Geometry: / { geometry++; bad += ($0 != "Geometry: " expected_geometry) }
        section == "screens" && /^Scale: / { scale++; bad += ($0 != "Scale: 1") }
        section == "screens" && /^Refresh Rate: / { refresh++; bad += ($0 != "Refresh Rate: " expected_refresh_millihz) }
        END { exit (bad || names != 1 || counts != 1 || screens != 1 || outputs != 1 ||
                    enabled != 1 || geometry != 1 || scale != 1 || refresh != 1) }
    ' "$1"; then
        echo "FAIL: backend=$backend output policy mismatch in $1" >&2
        return 1
    fi
}
owner()
{
    query org.freedesktop.DBus /org/freedesktop/DBus \
        org.freedesktop.DBus.GetConnectionUnixProcessID "$1"
}
case "$backend" in
virtual) set -- --virtual --width "$width" --height "$height" ;;
drm) set -- --drm ;;
esac
/usr/pkg/bin/kwin_wayland_wrapper "$@" \
    --xwayland --no-lockscreen '/bin/sh ./environment.sh' > compositor.log 2>&1 &
wrapper=$!
printf '%s\n' "$wrapper" > wrapper.pid
deadline=$(($(monotonic_seconds) + 100))
while :; do
    kill -0 "$wrapper"
    if [ -f display-env ] && owner org.kde.KWinWrapper > wrapper-owner.pid 2> query-error.log; then break; fi
    [ "$(monotonic_seconds)" -lt "$deadline" ] || { echo 'FAIL: KWin display environment deadline' >&2; exit 1; }
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
stamp compositor-ready
: > plasma-session.log
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
        "var emberExpectedWidth=${width-1280}; var emberExpectedHeight=${height-1024}; $(cat layout.js)" > layout.txt || return $?
    grep -qx "PASS: default desktop, panel and six applet models on ${width-1280}x${height-1024}" layout.txt || return $?
    render_health || return $?
}
phase=startup-readiness
while ! ready 2> readiness-error.log; do
    render_health || exit 1
    kill -0 "$wrapper" && kill -0 "$plasma"
    [ "$(monotonic_seconds)" -lt "$deadline" ] || { echo 'FAIL: full Plasma session readiness deadline' >&2; exit 1; }
    sleep 1
done
stamp session-ready
awk -F '\t' '$1 == "controller-start" { start=$2 } $1 == "session-ready" { printf "%.6f\n", $2-start }' phases.tsv > readiness-seconds.txt
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
backend_check support-before.txt
/bin/sh ./check-results.sh support support-before.txt "$profile"
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
backend_check support-after.txt
/bin/sh ./check-results.sh support support-after.txt "$profile"
shell_pid=$(cat org.kde.plasmashell.pid)
cat bus.log plasma-session.log compositor.log | awk -v prefix="[$shell_pid] " 'index($0, prefix) == 1' > shell-renderer.log
/bin/sh ./check-results.sh renderer shell-renderer.log "$profile"
# This API performs logout only. It does not request halt or reboot.
phase=logout
render_health || exit 1
query org.kde.Shutdown /Shutdown org.kde.Shutdown.logout > logout.log 2>&1
: > logout.requested
stamp logout-requested
deadline=$(($(monotonic_seconds) + 45))
while kill -0 "$wrapper" 2>/dev/null || kill -0 "$plasma" 2>/dev/null; do
    [ "$(monotonic_seconds)" -lt "$deadline" ] || { echo 'FAIL: normal Plasma logout deadline' >&2; exit 1; }
    sleep 1
done
wrapper_status=0
wait "$wrapper" || wrapper_status=$?
printf '%s\n' "$wrapper_status" > wrapper.status
plasma_status=0
wait "$plasma" || plasma_status=$?
printf '%s\n' "$plasma_status" > startplasma.status
[ "$wrapper_status" -eq 0 ]
[ "$plasma_status" -eq 0 ]
[ ! -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]
render_health || exit 1
stamp session-stopped
echo 'PASS: full session stayed ready for 30 seconds and completed normal logout'
