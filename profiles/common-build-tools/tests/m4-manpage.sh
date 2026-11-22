#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Run the exported recipe's manual-page hook for native and cross builds.
set -eu
if [ "$#" -ne 4 ]; then
    echo "usage: $0 EXPORTED_PKGSRC BMAKE SHELL NEW_WORK" >&2
    exit 2
fi
pkgsrc=$1
bmake=$2
shell=$3
work=$4
case "$shell" in
    /*) ;;
    *) echo "SHELL must be absolute" >&2; exit 2 ;;
esac
case "$shell" in
    *[!a-zA-Z0-9_./+-]*) echo "SHELL has unsupported characters" >&2; exit 2 ;;
esac
mkdir "$work"
recipe=$pkgsrc/devel/m4/Makefile
printf '.SHELL: name=sh path=%s\n.PHONY: pre-build\npre-build:\n' "$shell" > "$work/hook.mk"
# Keep the production condition as well as the commands. The former cross-only
# condition must fail the native freshness check below.
awk '
    /^# The release ships m4.1/ { copy = 1 }
    copy && /^# This is the target runtime shell/ { exit }
    copy { print }
' "$recipe" >> "$work/hook.mk"
grep -q '[$]{TEST} -s [$]{WRKSRC}/doc/m4.1' "$work/hook.mk"
grep -q '[$]{TOUCH} [$]{WRKSRC}/doc/m4.1' "$work/hook.mk"

for cross in no yes; do
    root=$work/$cross
    mkdir -p "$root/doc" "$root/src"
    printf 'Release manual\n' > "$root/doc/m4.1"
    cp "$root/doc/m4.1" "$root/expected"
    printf 'Patched source\n' > "$root/src/m4.c"
    touch -t 200001010000 "$root/doc/m4.1"
    touch -t 200001020000 "$root/src/m4.c"
    "$bmake" -r -f "$work/hook.mk" USE_CROSS_COMPILE="$cross" \
        WRKSRC="$root" TEST=/bin/test TOUCH=/usr/bin/touch pre-build
    cmp "$root/expected" "$root/doc/m4.1"
    if [ ! "$root/doc/m4.1" -nt "$root/src/m4.c" ]; then
        echo "manual remains older than patched source: cross=$cross" >&2
        exit 1
    fi
    for state in empty missing; do
        if [ "$state" = empty ]; then
            : > "$root/doc/m4.1"
        else
            rm "$root/doc/m4.1"
        fi
        if "$bmake" -r -f "$work/hook.mk" USE_CROSS_COMPILE="$cross" \
            WRKSRC="$root" TEST=/bin/test TOUCH=/usr/bin/touch pre-build \
            > "$root/$state.log" 2>&1; then
            echo "$state manual accepted: cross=$cross" >&2
            exit 1
        fi
        if [ "$state" = missing ] && [ -e "$root/doc/m4.1" ]; then
            echo "missing manual was created: cross=$cross" >&2
            exit 1
        fi
    done
done
echo "M4 native/cross manual freshness, contents and refusal: PASS"
