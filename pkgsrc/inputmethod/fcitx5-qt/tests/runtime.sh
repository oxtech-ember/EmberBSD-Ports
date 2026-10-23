#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check installed Qt6 input plugin selection.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 NEW_RESULT_DIRECTORY" >&2; exit 2; }
[ "$(id -u)" != 0 ] || { echo 'Run as an ordinary user' >&2; exit 2; }
case "$1" in /*) ;; *) echo 'An absolute result directory is required' >&2; exit 2 ;; esac
umask 077
mkdir "$1"
out=$(cd "$1" && pwd -P)
mkdir "$out/home" "$out/config" "$out/cache" "$out/data" "$out/runtime"
probe=/usr/pkg/bin/fcitx5-qt6-immodule-probing
wrapper=/usr/pkg/libexec/fcitx5-qt6-gui-wrapper
plugin=/usr/pkg/qt6/plugins/platforminputcontexts/libfcitx5platforminputcontextplugin.so
for item in "$probe" "$wrapper" /usr/pkg/bin/dbus-run-session /usr/bin/timeout; do
    [ -x "$item" ] || { echo "Missing executable: $item" >&2; exit 1; }
done
for item in "$probe" "$wrapper" "$plugin" /usr/pkg/lib/fcitx5/qt6/libfcitx-quickphrase-editor5.so; do
    [ -f "$item" ] || { echo "Missing installed file: $item" >&2; exit 1; }
    /usr/bin/ldd "$item" >> "$out/ldd.log" 2>&1
    if grep -F 'not found' "$out/ldd.log" >/dev/null; then
        echo 'Installed library resolution failed' >&2; exit 1
    fi
done
run() {
    name=$1 module=$2 expected=$3
    shift 3
    result=0
    env -i PATH=/usr/pkg/bin:/usr/bin:/bin LC_ALL=C HOME="$out/home" \
        XDG_CONFIG_HOME="$out/config" XDG_CACHE_HOME="$out/cache" \
        XDG_DATA_HOME="$out/data" XDG_RUNTIME_DIR="$out/runtime" \
        QT_QPA_PLATFORM=offscreen QT_IM_MODULE="$module" \
        QT_PLUGIN_PATH=/usr/pkg/qt6/plugins \
        LD_LIBRARY_PATH=/usr/pkg/lib:/usr/pkg/qt6/lib:/usr/pkg/gcc16/lib \
        /usr/bin/timeout -k 5 30 /usr/pkg/bin/dbus-run-session -- "$@" \
        > "$out/$name.log" 2>&1 || result=$?
    printf '%s\t%s\n' "$name" "$result" >> "$out/status.tsv"
    [ "$result" = "$expected" ] || {
        echo "FAIL: $name returned $result, expected $expected" >&2; exit 1
    }
}
run selected-input-context fcitx5 0 "$probe"
grep -F -x 'QT_QPA_PLATFORM=offscreen' "$out/selected-input-context.log"
grep -F -x 'IM_MODULE_CLASSNAME=fcitx::QFcitxPlatformInputContext' "$out/selected-input-context.log"
run missing-input-context ember-missing-input-plugin 0 "$probe"
if grep -F -x 'IM_MODULE_CLASSNAME=fcitx::QFcitxPlatformInputContext' "$out/missing-input-context.log" >/dev/null; then
    echo 'FAIL: missing plugin control still selected Fcitx' >&2; exit 1
fi
run wrapper-help fcitx5 0 "$wrapper" --help
grep -F 'Usage:' "$out/wrapper-help.log"
run quickphrase-metadata fcitx5 0 "$wrapper" --test quickphrase/editor
run missing-metadata fcitx5 1 "$wrapper" --test ember-missing-addon/invalid
printf 'PASS: installed input context, missing-plugin control, help, quickphrase metadata, missing-metadata control\n'
printf 'Offscreen only. No physical input, Wayland session, rendered widget, or memory-analysis result.\n'
