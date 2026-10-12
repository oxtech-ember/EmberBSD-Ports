#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), isolated installed QML plugin acceptance.
set -eu
[ "$#" = 2 ] || { echo 'Usage: run.sh ABSOLUTE_MIME_BINARY NEW_OUTPUT' >&2; exit 2; }
binary=$1
case "$binary" in /*) ;; *) exit 2 ;; esac
[ -x "$binary" ]
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
umask 077
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
ulimit -c 0
sysctl kern.boottime > "$work/boot.before"
pkg_info -e plasma6-milou > "$work/packages.txt"
pkg_admin check plasma6-milou > "$work/package-check.txt" 2>&1
for run in first second wrong-config; do
    out="$work/$run"
    mkdir "$out" "$out/home" "$out/runtime" "$out/config"
    value='ember-alpha,ember-β'
    [ "$run" != wrong-config ] || value='deliberately-wrong'
    printf '[Plugins][Favorites]\nplugins=%s\n' "$value" > "$out/config/krunnerrc"
    result=0
    timeout -k 5 90 env -i PATH="$PATH" HOME="$out/home" LC_ALL=C.UTF-8 \
        XDG_RUNTIME_DIR="$out/runtime" XDG_CONFIG_HOME="$out/config" \
        XDG_DATA_DIRS=/usr/pkg/share QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
        dbus-run-session -- qmltestrunner -input "$src/tst_ResultsModel.qml" \
        > "$out/test.log" 2>&1 || result=$?
    printf '%s\n' "$result" > "$out/status"
    cat "$out/test.log"
    if [ "$run" = wrong-config ]; then
        [ "$result" -gt 0 ] && [ "$result" -lt 124 ]
        grep -q 'FAIL!.*InstalledMilou::test_configuredFavorites' "$out/test.log"
    else
        [ "$result" = 0 ]
        grep -q '0 failed' "$out/test.log"
    fi
done
mkdir "$work/mime" "$work/mime/home" "$work/mime/runtime"
timeout -k 5 60 env -i PATH="$PATH" HOME="$work/mime/home" LC_ALL=C.UTF-8 \
    XDG_RUNTIME_DIR="$work/mime/runtime" QT_QPA_PLATFORM=offscreen \
    dbus-run-session -- "$binary" > "$work/mime/test.log" 2>&1
cat "$work/mime/test.log"
sha256 "$binary" "$src/tst_ResultsModel.qml" "$src/run.sh" > "$work/inputs.sha256"
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: installed Milou QML/KConfig, wrong-config rejection and MIME conversion; offscreen software, no desktop or GPU claim'
