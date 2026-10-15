#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Bounded, process-local V3D allocation diagnosis.
set -eu
[ "$#" -eq 3 ] || {
    echo "Usage: $0 ABSOLUTE_TRACE_SO NEW_ABSOLUTE_OUTPUT 1280x1024|640x480" >&2
    exit 2
}
trace=$1 work=$2
case "$3" in
    1280x1024) width=1280 height=1024 ;;
    640x480) width=640 height=480 ;;
    *) echo 'Unsupported diagnostic dimensions' >&2; exit 2 ;;
esac
for path in "$trace" "$work"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
[ -f "$trace" ] || { echo 'Missing tracing library' >&2; exit 2; }
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Output exists' >&2; exit 2; }
for program in /usr/bin/timeout /usr/pkg/bin/dbus-run-session \
    /usr/pkg/bin/kwin_wayland /usr/pkg/qt6/bin/qdbus; do
    [ -x "$program" ] || { echo "Missing executable: $program" >&2; exit 2; }
done
umask 077
mkdir "$work"
work=$(CDPATH= cd -- "$work" && pwd)
for directory in home runtime config cache data state; do
    mkdir "$work/$directory"
done
cat > "$work/client.sh" <<'CLIENT'
#!/bin/sh
set -eu
# This diagnostic traces KWin, not the D-Bus query.
unset LD_PRELOAD
trap 'status=$?; printf "%s\n" "$status" > client.status' 0
/usr/bin/timeout -k 1 8 /usr/pkg/qt6/bin/qdbus \
    org.kde.KWin /KWin org.kde.KWin.supportInformation \
    > supportinformation.txt 2>&1
CLIENT
cd "$work"
status=0
# Keep stderr on a regular private file. Do not pipe it to a short-lived reader.
# The normal timeout and the forced-kill delay total at most 30 seconds.
/usr/bin/timeout -k 2 28 /usr/bin/env -i \
    PATH=/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/bin:/usr/sbin:/bin:/sbin \
    HOME="$work/home" LC_ALL=C.UTF-8 XDG_RUNTIME_DIR="$work/runtime" \
    XDG_CONFIG_HOME="$work/config" XDG_CACHE_HOME="$work/cache" \
    XDG_DATA_HOME="$work/data" XDG_STATE_HOME="$work/state" \
    XDG_DATA_DIRS=/usr/pkg/share XDG_CONFIG_DIRS=/usr/pkg/etc/xdg \
    /usr/pkg/bin/dbus-run-session -- /usr/bin/env LD_PRELOAD="$trace" \
    /usr/pkg/bin/kwin_wayland --virtual --width "$width" --height "$height" \
    --socket wayland-0 --no-lockscreen --exit-with-session='/bin/sh ./client.sh' \
    > compositor.stdout 2> compositor.stderr || status=$?
printf '%s\n' "$status" > status
printf 'Diagnostic directory: %s\nKWin status: %s\n' "$work" "$status"
exit "$status"
