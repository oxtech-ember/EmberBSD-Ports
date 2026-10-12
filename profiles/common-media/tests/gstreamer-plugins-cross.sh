#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check production generators and complete PLIST.
set -eu
[ "$#" = 2 ] || { echo 'Usage: gstreamer-plugins-cross.sh PKGSRC NEW_WORK' >&2; exit 2; }
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set cross MAKECONF}"
tree=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
for family in base bad; do
    recipe=$tree/multimedia/gst-plugins1-$family
    get() { "$BMAKE" -C "$recipe" -V "\${$1}"; }
    [ "$(get PKGNAME)" = gst-plugins1-$family-1.28.8nb1 ]
    stage=$(get DESTDIR)$(get PREFIX)
    host=$(get TOOLBASE)
    for tool in glib-mkenums glib-genmarshal g-ir-scanner g-ir-compiler; do
        [ "$(get "MESON_BINARY.$tool")" = "$host/bin/$tool" ]
        [ -x "$host/bin/$tool" ]
    done
    [ -z "$("$BMAKE" -C "$recipe" USE_CROSS_COMPILE=no -V '${MESON_BINARIES}')" ]
    grep '^lib/girepository-1.0/.*\.typelib$' "$recipe/PLIST" > "$work/$family-typelibs.txt"
    case "$family" in base) count=9 ;; bad) count=11 ;; esac
    [ "$(wc -l < "$work/$family-typelibs.txt" | tr -d ' ')" = "$count" ]
    while read -r file; do
        [ -s "$stage/$file" ]
        namespace=$(basename "$file" .typelib)
        [ -s "$stage/share/gir-1.0/$namespace.gir" ]
        grep -q '<enumeration\|<class\|<record' "$stage/share/gir-1.0/$namespace.gir"
    done < "$work/$family-typelibs.txt"
    # Every unconditional file from the source-controlled package list survives.
    awk '/^[a-z]/ && !/\$/ {print}' "$recipe/PLIST" > "$work/$family-files.txt"
    while read -r file; do [ -e "$stage/$file" ]; done < "$work/$family-files.txt"
    echo "PASS: $family host generators, native selection, $count GIR/typelibs and full package files"
done
