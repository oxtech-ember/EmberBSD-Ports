#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Plasma Desktop virtual-output acceptance.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 ABSOLUTE_NEW_OUTPUT ABSOLUTE_PIXEL_CHECKER" >&2; exit 2; }
work=$1
pixel_checker=$2
case "$pixel_checker" in /*) ;; *) echo 'Absolute pixel checker required.' >&2; exit 2 ;; esac
[ -x "$pixel_checker" ] || { echo 'Missing pixel checker.' >&2; exit 2; }
case "$work" in /*) ;; *) echo 'Absolute output path required.' >&2; exit 2 ;; esac
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Output already exists.' >&2; exit 2; }
[ "$(id -u)" -ne 0 ] || { echo 'Run this test as a non-root desktop user.' >&2; exit 2; }
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for file in session.sh layout.js capture-layout.js check-results.sh; do
    [ -f "$source_dir/$file" ] || { echo "Missing test input: $file" >&2; exit 2; }
done
for program in /usr/bin/timeout /usr/pkg/bin/dbus-run-session /usr/pkg/bin/kwin_wayland \
    /usr/pkg/bin/plasmashell /usr/pkg/qt6/bin/qdbus; do
    [ -x "$program" ] || { echo "Missing executable: $program" >&2; exit 2; }
done
umask 077
mkdir "$work"
work=$(CDPATH= cd -- "$work" && pwd)
for directory in home runtime config cache data state; do mkdir "$work/$directory"; done
for file in session.sh layout.js capture-layout.js check-results.sh; do cp "$source_dir/$file" "$work/$file"; done
cp "$pixel_checker" "$work/capture-pixels"
cd "$work"
uname -a > system.txt
id > user.txt
/sbin/sysctl kern.boottime > boot.before
/usr/bin/cksum -a SHA256 /usr/pkg/bin/kwin_wayland /usr/pkg/bin/plasmashell \
    /usr/pkg/qt6/bin/qdbus session.sh layout.js capture-layout.js check-results.sh > inputs.sha256
status=0
/usr/bin/timeout -k 5 240 /usr/bin/env -i \
    PATH=/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin \
    HOME="$work/home" LC_ALL=C.UTF-8 XDG_RUNTIME_DIR="$work/runtime" \
    XDG_CONFIG_HOME="$work/config" XDG_CONFIG_DIRS=/usr/pkg/etc/xdg \
    XDG_CACHE_HOME="$work/cache" XDG_DATA_HOME="$work/data" XDG_STATE_HOME="$work/state" \
    XDG_DATA_DIRS=/usr/pkg/share XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=KDE \
    QT_QPA_PLATFORM=wayland QSG_RHI_BACKEND=opengl QSG_INFO=1 \
    EMBER_PLASMA_OUTPUT="$work" \
    /usr/pkg/bin/dbus-run-session -- /usr/pkg/bin/kwin_wayland \
    --virtual --width 1280 --height 1024 --socket wayland-0 --no-lockscreen \
    --exit-with-session='/bin/sh ./session.sh' > compositor.log 2>&1 || status=$?
printf '%s\n' "$status" > status
/sbin/sysctl kern.boottime > boot.after
cmp boot.before boot.after
cat compositor.log
[ ! -f plasmashell.log ] || cat plasmashell.log
[ "$status" -eq 0 ] || { echo "FAIL: KWin session exited $status" >&2; exit 1; }
[ -f client.status ] && [ "$(cat client.status)" = 0 ]
[ -f plasmashell.status ] && [ "$(cat plasmashell.status)" = 0 ]
[ ! -S runtime/wayland-0 ] || { echo 'FAIL: Wayland socket remains.' >&2; exit 1; }
/bin/sh ./check-results.sh support supportinformation-after.txt
/bin/sh ./check-results.sh renderer plasmashell.log
/bin/sh ./check-results.sh png desktop.png
./capture-pixels desktop.png
/usr/bin/cksum -a SHA256 desktop.png > desktop.sha256
echo 'PASS: Plasma Desktop on KWin OpenGL/V3D; virtual output only'
