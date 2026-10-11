#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run on the installed EmberBSD target.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 ABSOLUTE_CONSUMER NEW_OUTPUT" >&2; exit 2; }
consumer=$1 output=$2
case "$consumer" in /*) ;; *) exit 2;; esac
mkdir "$output"
unset LD_LIBRARY_PATH QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH
"$consumer" > "$output/normal.log" 2>&1
"$consumer" > "$output/restart.log" 2>&1
set +e
"$consumer" --no-plugins > "$output/missing-plugins.log" 2>&1
status=$?
set -e
[ "$status" = 3 ] || { echo "Missing-plugin control returned $status, expected 3" >&2; exit 1; }
for log in normal restart; do
    [ "$(grep -c '^PASS cycle' "$output/$log.log")" = 4 ]
    grep -q '^loaded=/usr/pkg/qt6/lib/libQt6Core.so' "$output/$log.log"
    grep -q '^loaded=/usr/pkg/qt6/plugins/imageformats/libqsvg.so' "$output/$log.log"
done
/usr/pkg/qt6/bin/qmake -query QT_VERSION > "$output/qmake-version.txt"
[ "$(cat "$output/qmake-version.txt")" = 6.12.0 ]
sed -n 's/^loaded=//p' "$output/normal.log" | sort -u | while IFS= read -r library; do
    [ -f "$library" ] || { echo "Missing loaded library: $library" >&2; exit 1; }
    sha256 "$library"
done > "$output/libraries.sha256"
sha256 "$consumer" > "$output/consumer.sha256"
printf '%s\n' 'PASS: installed Qt 6.12 Core/Gui/SVG, thread signals, resources, pixels, plugin rejection and restart'
