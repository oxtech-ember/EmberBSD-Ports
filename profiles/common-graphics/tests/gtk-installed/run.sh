#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run unchanged upstream GTK test programs.
set -eu
[ "$#" -eq 1 ] || { echo "Usage: $0 NEW_OUTPUT_DIRECTORY" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case "$1" in /*) output=$1 ;; *) echo 'Use an absolute output path.' >&2; exit 2 ;; esac
[ ! -e "$output" ] || { echo 'Output already exists.' >&2; exit 2; }
[ -n "${DISPLAY:-}" ] || { echo 'DISPLAY is required.' >&2; exit 2; }
for tool in /usr/bin/timeout /usr/bin/ldd /usr/bin/sha256; do
    [ -x "$tool" ] || { echo "Missing target tool: $tool" >&2; exit 2; }
done
while read -r expected relative; do
    actual=$(/usr/bin/sha256 -q "$root/$relative")
    [ "$actual" = "$expected" ] || { echo "Payload hash differs: $relative" >&2; exit 2; }
done < "$root/SHA256"
mkdir "$output"
unset LD_LIBRARY_PATH LD_PRELOAD
export GDK_BACKEND=x11 GIO_USE_VOLUME_MONITOR=unix GSETTINGS_BACKEND=memory
export GTK_CSD=1 G_ENABLE_DIAGNOSTIC=0 GSK_RENDERER=cairo GTK_TEST_MESON=1
G_TEST_SRCDIR=$root/source/testsuite/gtk
G_TEST_BUILDDIR=$root/bin
GSETTINGS_SCHEMA_DIR=$root/schemas
export G_TEST_SRCDIR G_TEST_BUILDDIR GSETTINGS_SCHEMA_DIR
failed=0
for pair in 'builder 39' 'entry 2' 'textbuffer 11' 'treepath 6' 'window 7'; do
    set -- $pair
    name=$1
    expected=$2
    if /usr/bin/timeout -k 5 10 /usr/bin/ldd "$root/bin/$name" \
        > "$output/$name.ldd" 2>&1; then
        loader_status=0
    else
        loader_status=$?
    fi
    printf '%s\n' "$loader_status" > "$output/$name.loader-status"
    if [ "$loader_status" -ne 0 ] ||
        ! grep -q '/usr/pkg/lib/libgtk-3[.]so' "$output/$name.ldd" ||
        grep -q 'not found' "$output/$name.ldd"; then
        echo "FAIL: $name installed loader; inspect $output/$name.ldd"
        failed=1
        continue
    fi
    if /usr/bin/timeout -k 5 30 "$root/bin/$name" --tap -k \
        > "$output/$name.tap" 2> "$output/$name.stderr"; then
        status=0
    else
        status=$?
    fi
    printf '%s\n' "$status" > "$output/$name.status"
    if awk -v expected="$expected" '
        /^1\.\.[0-9]+$/ { plan=$0; sub(/^1\.\./, "", plan); plans++ }
        /^ok [0-9]+/ { passed++; if ($0 ~ /#[[:space:]]*SKIP/) skipped++ }
        /^not ok / { bad++ }
        /^Bail out!/ { bad++ }
        END {
            printf "plan=%d passed=%d skipped=%d failed=%d expected=%d\n", plan, passed, skipped, bad, expected;
            exit !(plans==1 && plan==expected && passed==expected && skipped==0 && bad==0)
        }' "$output/$name.tap" > "$output/$name.counts" && [ "$status" -eq 0 ]; then
        echo "PASS: $name ($expected upstream tests)"
    else
        echo "FAIL: $name status=$status; inspect $output/$name.tap and .stderr"
        failed=1
    fi
done
if [ "$failed" -eq 0 ]; then
    echo 'PASS: 65 unchanged upstream GTK tests with installed libraries'
fi
exit "$failed"
