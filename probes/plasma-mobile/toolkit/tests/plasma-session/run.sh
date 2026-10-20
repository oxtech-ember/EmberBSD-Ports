#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Installed classic Plasma session acceptance.
set -eu
[ "$#" -eq 1 ] || { echo "Usage: $0 ABSOLUTE_NEW_OUTPUT" >&2; exit 2; }
work=$1
case "$work" in /*) ;; *) echo 'Absolute output path required.' >&2; exit 2 ;; esac
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Output already exists.' >&2; exit 2; }
[ "$(id -u)" -ne 0 ] || { echo 'Run as an ordinary desktop user.' >&2; exit 2; }
# KWin and D-Bus use Unix sockets with bounded path lengths.
[ "${#work}" -le 70 ] || { echo 'Use an output path of at most 70 characters.' >&2; exit 2; }
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# KWin creates Xwayland sockets as this user. Boot must prepare their parents.
for directory in /tmp /tmp/.X11-unix /tmp/.ICE-unix; do
    if [ -L "$directory" ] || [ ! -d "$directory" ] ||
        [ "$(/usr/bin/stat -f '%u:%g:%p' "$directory" 2>/dev/null)" != '0:0:41777' ]; then
        echo "Missing or unsafe X11 runtime directory: $directory" >&2
        echo 'Ask root to activate the Xwayland x11_runtime rc.d service and run /etc/rc.d/x11_runtime start.' >&2
        exit 2
    fi
done
for name in timeout; do [ -x "/usr/bin/$name" ]; done
for name in perl dbus-run-session kwin_wayland_wrapper kwin_wayland Xwayland \
    startplasma-wayland plasma_session ksmserver kded6 plasmashell \
    plasma-shutdown; do
    [ -x "/usr/pkg/bin/$name" ] || { echo "Missing executable: $name" >&2; exit 2; }
done
[ -x /usr/pkg/qt6/bin/qdbus ]
# Probe the bus daemon itself. Do not activate a system service or create output.
# Qt qdbus accepts --system before the service, object and qualified method.
if system_bus_id=$(/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
    /usr/bin/timeout -k 2 5 /usr/pkg/qt6/bin/qdbus --system \
    org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.GetId); then
    if [ "${#system_bus_id}" -ne 32 ] ||
        ! printf '%s\n' "$system_bus_id" | grep -Eq '^[0-9a-f]{32}$'; then
        echo 'FAIL: system-bus preflight returned an invalid bus ID' >&2
        exit 2
    fi
else
    system_bus_status=$?
    echo "FAIL: system-bus preflight status=$system_bus_status; start the installed dbus rc.d service" >&2
    exit 2
fi
[ -x /usr/pkg/libexec/kactivitymanagerd ]
# Existing packages and the current cross linker use these two interpreter
# paths. Require the installed base to supply both; never make aliases here.
for loader in /usr/libexec/ld.elf_so /libexec/ld.elf_so; do
    [ -x "$loader" ] || { echo "Missing base ELF loader: $loader" >&2; exit 2; }
done
account=$(id -un)
login_shell=$(/usr/pkg/bin/perl -e 'my @p = getpwuid($<); @p && $p[8] =~ m{^/} or die "Invalid account shell\n"; print $p[8]')
[ -x "$login_shell" ] || { echo 'Account shell is not executable.' >&2; exit 2; }
for file in guard.pl controller.sh environment.sh; do [ -f "$source_dir/$file" ]; done
for file in layout.js check-results.sh; do [ -f "$source_dir/../plasma-desktop/$file" ]; done
umask 077
mkdir "$work"
work=$(CDPATH= cd -- "$work" && pwd)
for directory in home runtime config cache data state tmp; do mkdir "$work/$directory"; done
for file in guard.pl controller.sh environment.sh; do cp "$source_dir/$file" "$work/$file"; done
for file in layout.js check-results.sh; do cp "$source_dir/../plasma-desktop/$file" "$work/$file"; done
printf '[General]\nsystemdBoot=false\n' > "$work/config/startkderc"
cd "$work"
printf '%s\n' "$system_bus_id" > system-bus-id.txt
id > user.txt
uname -a > system.txt
ls -l /usr/libexec/ld.elf_so /libexec/ld.elf_so > base-loaders.txt
/usr/bin/cksum -a SHA256 /usr/libexec/ld.elf_so /libexec/ld.elf_so > base-loaders.sha256
/sbin/sysctl kern.boottime > boot.before
/usr/bin/cksum -a SHA256 /usr/pkg/bin/startplasma-wayland /usr/pkg/bin/plasma_session \
    /usr/pkg/bin/kwin_wayland_wrapper /usr/pkg/bin/kwin_wayland /usr/pkg/bin/Xwayland \
    /usr/pkg/bin/plasmashell /usr/pkg/bin/ksmserver /usr/pkg/libexec/kactivitymanagerd \
    guard.pl controller.sh environment.sh layout.js check-results.sh > inputs.sha256
status=0
/usr/bin/env -i PATH=/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin \
    HOME="$work/home" USER="$account" LOGNAME="$account" SHELL="$login_shell" LC_ALL=C.UTF-8 TMPDIR="$work/tmp" XDG_RUNTIME_DIR="$work/runtime" \
    XDG_CONFIG_HOME="$work/config" XDG_CONFIG_DIRS=/usr/pkg/etc/xdg \
    XDG_CACHE_HOME="$work/cache" XDG_DATA_HOME="$work/data" XDG_STATE_HOME="$work/state" \
    XDG_DATA_DIRS=/usr/pkg/share XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=KDE \
    QT_QPA_PLATFORM=wayland QSG_RHI_BACKEND=opengl QSG_INFO=1 \
    QT_MESSAGE_PATTERN='[%{pid}] %{category}: %{message}' EMBER_PLASMA_OUTPUT="$work" \
    /usr/pkg/bin/perl ./guard.pl "$work" 240 -- \
    /usr/pkg/bin/dbus-run-session -- /bin/sh ./controller.sh > bus.log 2>&1 || status=$?
printf '%s\n' "$status" > status
/sbin/sysctl kern.boottime > boot.after
# This live runner waits for one non-resumable guard process. A reboot cannot
# return through that wait. Civil kern.boottime can change after a clock step.
if cmp -s boot.before boot.after; then
    echo unchanged
else
    echo changed
fi > boot-time-change.txt
cat bus.log
[ "$status" -eq 0 ]
[ "$(cat guard.status)" = 0 ]
[ "$(cat controller.status)" = 0 ]
[ "$(cat wrapper.status)" = 0 ]
[ "$(cat startplasma.status)" = 0 ]
[ -f logout.requested ]
if find runtime -type s | grep -q .; then
    echo 'FAIL: a private runtime socket remains.' >&2
    exit 1
fi
/bin/sh ./check-results.sh support support-after.txt
/bin/sh ./check-results.sh renderer shell-renderer.log
echo 'PASS: installed classic Plasma session, V3D, Xwayland, Activities and logout; virtual output only'
