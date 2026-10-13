#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Private KWin/V3D virtual-output acceptance.
set -eu

[ "$#" -eq 3 ] || {
    echo "Usage: $0 ABSOLUTE_QT_QUICK_BINARY ABSOLUTE_QT_QUICK_RUNNER NEW_OUTPUT" >&2
    exit 2
}
binary=$1 runner=$2 work=$3
for path in "$binary" "$runner" "$work"; do
    case "$path" in
        /*) ;;
        *) echo "Absolute path required: $path" >&2; exit 2 ;;
    esac
done
[ -x "$binary" ] && [ -f "$runner" ] || {
    echo 'The Qt Quick executable and runner must exist.' >&2
    exit 2
}
[ ! -e "$work" ] && [ ! -L "$work" ] || {
    echo "Output already exists: $work" >&2
    exit 2
}
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
trap 'status=$?; printf "%s\n" "$status" > "$EMBER_KWIN_OUTPUT/client.status"' 0
export WAYLAND_DISPLAY=wayland-0
[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]
/usr/bin/timeout -k 2 15 /usr/pkg/qt6/bin/qdbus \
    org.kde.KWin /KWin org.kde.KWin.supportInformation \
    > "$EMBER_KWIN_OUTPUT/supportinformation.txt" 2>&1
grep -q '^Compositing is active$' "$EMBER_KWIN_OUTPUT/supportinformation.txt"
grep -q '^Compositing Type: OpenGL$' "$EMBER_KWIN_OUTPUT/supportinformation.txt"
grep -q '^OpenGL renderer string:.*V3D ' "$EMBER_KWIN_OUTPUT/supportinformation.txt"
/bin/sh "$EMBER_QUICK_RUNNER" "$EMBER_QUICK_BINARY" "$EMBER_KWIN_OUTPUT/client" \
    > "$EMBER_KWIN_OUTPUT/client.log" 2>&1
CLIENT

cd "$work"
/sbin/sysctl kern.boottime > boot.before
status=0
# KWin parses the session command. Keep it constant; pass all caller paths
# through the environment so spaces do not become extra command arguments.
/usr/bin/timeout -k 5 240 /usr/bin/env -i \
    PATH=/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin \
    HOME="$work/home" LC_ALL=C.UTF-8 XDG_RUNTIME_DIR="$work/runtime" \
    XDG_CONFIG_HOME="$work/config" XDG_CACHE_HOME="$work/cache" \
    XDG_DATA_HOME="$work/data" XDG_STATE_HOME="$work/state" XDG_DATA_DIRS=/usr/pkg/share \
    EMBER_KWIN_OUTPUT="$work" EMBER_QUICK_RUNNER="$runner" EMBER_QUICK_BINARY="$binary" \
    /usr/pkg/bin/dbus-run-session -- /usr/pkg/bin/kwin_wayland \
    --virtual --width 1280 --height 1024 --socket wayland-0 --no-lockscreen \
    --exit-with-session='/bin/sh ./client.sh' > compositor.log 2>&1 || status=$?
printf '%s\n' "$status" > status
/sbin/sysctl kern.boottime > boot.after
cmp boot.before boot.after
cat compositor.log
[ ! -f client.log ] || cat client.log
[ "$status" -eq 0 ] || { echo "FAIL: KWin session exited $status" >&2; exit 1; }
[ -f client.status ] && [ "$(cat client.status)" = 0 ] || {
    echo 'FAIL: the session child did not finish successfully' >&2
    exit 1
}
grep -q '^Compositing is active$' supportinformation.txt
grep -q '^Compositing Type: OpenGL$' supportinformation.txt
grep -q '^OpenGL renderer string:.*V3D ' supportinformation.txt
grep -q '^PASS: two Qt Quick GPU processes' client.log
[ ! -S runtime/wayland-0 ] || {
    echo 'FAIL: KWin left its Wayland socket behind' >&2
    exit 1
}
echo 'PASS: KWin OpenGL/V3D and Qt Quick scene/layer pixels; virtual output only, no HDMI or Plasma acceptance'
