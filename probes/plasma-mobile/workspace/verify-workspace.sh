#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# These are real loader/QML/clock checks, not compositor or hardware validation.
set -eu
umask 077
: "${WORKSPACE_ROOT:=$HOME/.cache/emberbsd-plasma-workspace}"
: "${PLASMA_PREFIX:=$HOME/.cache/emberbsd-plasma-current/install}"
recipe_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
prefix="$WORKSPACE_ROOT/prefix"
mkdir -p "$WORKSPACE_ROOT"
probe_root=$(mktemp -d "$WORKSPACE_ROOT/runtime-probe.XXXXXX")
log_dir="$probe_root/logs"
mkdir "$probe_root/config" "$probe_root/data" "$probe_root/cache" "$probe_root/run" "$log_dir"
printf 'Workspace verification logs: %s\n' "$log_dir"
export PATH="$prefix/bin:$PLASMA_PREFIX/bin:/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/X11R7/bin:/usr/bin:/bin"
export LD_LIBRARY_PATH="$prefix/lib:$PLASMA_PREFIX/lib:/usr/pkg/lib:/usr/pkg/qt6/lib:/usr/X11R7/lib"
export LD_BIND_NOW=1
export QT_PLUGIN_PATH="$prefix/lib/qt6/plugins:$PLASMA_PREFIX/lib/qt6/plugins:/usr/pkg/qt6/plugins"
export QML_IMPORT_PATH="$prefix/lib/qt6/qml:$PLASMA_PREFIX/lib/qt6/qml:/usr/pkg/qt6/qml"
export XDG_DATA_DIRS="$prefix/share:$PLASMA_PREFIX/share:/usr/pkg/share:/usr/share"
export XDG_CONFIG_HOME="$probe_root/config" XDG_DATA_HOME="$probe_root/data" XDG_CACHE_HOME="$probe_root/cache"
export XDG_RUNTIME_DIR="$probe_root/run"
export LC_ALL=C.UTF-8 XDG_CURRENT_DESKTOP=KDE
export QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software
unset DISPLAY WAYLAND_DISPLAY WAYLAND_SOCKET QML2_IMPORT_PATH
unset DBUS_SESSION_BUS_ADDRESS DBUS_SESSION_BUS_PID DBUS_SESSION_BUS_WINDOWID
unset DBUS_STARTER_ADDRESS DBUS_STARTER_BUS_TYPE
unset QT_LOGGING_RULES QT_LOGGING_CONF QT_MESSAGE_PATTERN PLASMA_SESSION_GUI_TEST
command -v timeout >/dev/null
timeout -k 2 30 ldd "$prefix/bin/plasmashell" > "$log_dir/workspace-ldd.log" 2>&1
if ! awk '
    /not found/ { missing = 1 }
    /stdc\+\+/ {
        runtimes++
        if ($1 == "-lstdc++.9" && $2 == "=>" && $3 == "/usr/lib/libstdc++.so.9") {
            expected++
        }
    }
    END { exit !(runtimes == 1 && expected == 1 && !missing) }
' "$log_dir/workspace-ldd.log"; then
    echo 'Expected exactly one system libstdc++.so.9 and no missing libraries; inspect workspace-ldd.log' >&2
    exit 1
fi
timeout -k 2 30 dbus-run-session -- "$prefix/bin/plasmashell" --version > "$log_dir/workspace-version.log" 2>&1
grep -Fx 'plasmashell 6.8.3' "$log_dir/workspace-version.log" >/dev/null
timeout -k 2 30 dbus-run-session -- qml "$recipe_dir/module-probe.qml" > "$log_dir/workspace-modules.log" 2>&1
grep -F 'qml: Workspace QML imports and model constructors succeeded ' "$log_dir/workspace-modules.log" >/dev/null
timeout -k 2 30 dbus-run-session -- qml "$recipe_dir/clock-probe.qml" > "$log_dir/workspace-clock.log" 2>&1
grep -Fx 'qml: Workspace Clock advanced across three distinct seconds' "$log_dir/workspace-clock.log" >/dev/null
if grep -F 'qmlRegisterType requires absolute URLs' "$log_dir/workspace-version.log" "$log_dir/workspace-modules.log" "$log_dir/workspace-clock.log"; then
    echo 'Invalid QML type registration detected' >&2
    exit 1
fi
cat "$log_dir/workspace-version.log" "$log_dir/workspace-modules.log" "$log_dir/workspace-clock.log"
echo 'Workspace verification passed'
