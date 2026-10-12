#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Isolated KWin Wayland session acceptance on a
# board without an accepted KMS driver: kwin_wayland runs on the virtual
# backend inside a private dbus-run-session, one Qt Quick client renders real
# pixels through the compositor, and KWin exits when the client wrapper exits.
# The board has no accepted hardware GPU stack yet, so the session runs on
# software EGL (llvmpipe) and this file makes no hardware acceleration claim.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 ABSOLUTE_CLIENT_BINARY NEW_WORK" >&2; exit 2; }
binary=$1 work=$2
case "$binary:$work" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
umask 077
mkdir "$work"
mkdir "$work/runtime" "$work/config" "$work/cache" "$work/data" "$work/state" "$work/home"
cat > "$work/client.sh" <<'CLIENT'
#!/bin/sh
set -eu
i=0
while [ ! -S "$XDG_RUNTIME_DIR/wayland-0" ] && [ "$i" -lt 150 ]; do
    i=$((i + 1))
    sleep 0.2
done
[ -S "$XDG_RUNTIME_DIR/wayland-0" ]
export WAYLAND_DISPLAY=wayland-0
sh "$EMBER_QUICK_RUNNER" "$EMBER_QUICK_BINARY" "$PWD/client" > client.log 2>&1
/usr/pkg/qt6/bin/qdbus org.kde.KWin /KWin org.kde.KWin.supportInformation > supportinformation.txt 2>&1 || true
CLIENT
chmod 0700 "$work/client.sh"
cd "$work"
/usr/bin/timeout -k 5 240 /usr/bin/env -i \
    PATH=/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin HOME="$work/home" \
    XDG_RUNTIME_DIR="$work/runtime" XDG_CONFIG_HOME="$work/config" \
    XDG_CACHE_HOME="$work/cache" XDG_DATA_HOME="$work/data" \
    XDG_STATE_HOME="$work/state" XDG_DATA_DIRS=/usr/pkg/share LIBGL_ALWAYS_SOFTWARE=1 \
    EMBER_QUICK_RUNNER="$src/../qt-quick-gpu/run-zero3w.sh" EMBER_QUICK_BINARY="$binary" \
    /usr/pkg/bin/dbus-run-session -- /usr/pkg/bin/kwin_wayland \
    --virtual --no-lockscreen --no-kactivities --no-global-shortcuts \
    --exit-with-session="$PWD/client.sh" > compositor.log 2>&1
cat client.log
grep -q '^PASS: two Qt Quick software-EGL processes' client.log
grep -q '^renderer=llvmpipe' client/normal.log
[ -s supportinformation.txt ]
grep -q 'KWin' supportinformation.txt
grep -q 'Compositing is active' supportinformation.txt
# Upstream VirtualBackend only offers OpenGL compositing when a DRM render
# node exists; this board has no DRM driver yet, so the compositor must be
# active on QPainter while the clients below use real (software) EGL.
grep -q 'Compositing Type: QPainter' supportinformation.txt
[ ! -S "$work/runtime/wayland-0" ]
/usr/bin/sha256 "$binary" > "$work/binary-sha256.txt"
echo 'PASS: private KWin Wayland session on the virtual backend: active QPainter compositor, Qt Quick client EGL pixels via llvmpipe, clean exit; hardware GL compositing needs the DRM render node (pending)'
