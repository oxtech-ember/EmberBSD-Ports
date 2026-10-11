#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the actual target Qt configuration.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 QT_BUILD HOST_QT SYSROOT WAYLAND_SCANNER" >&2; exit 2; }
cache=$1/CMakeCache.txt host=$2 sysroot=$3 scanner=$4
[ -s "$cache" ]
for pair in "QT_HOST_PATH:PATH=$host" "CMAKE_SYSROOT:PATH=$sysroot" \
    "WaylandScanner_EXECUTABLE:FILEPATH=$scanner" 'QT_FORCE_BUILD_TOOLS:BOOL=ON'; do
    grep -Fx -- "$pair" "$cache"
done
for feature in wayland_client wayland_egl egl gbm eglfs_egldevice eglfs_gbm; do
    grep -Fx "QT_FEATURE_$feature:INTERNAL=ON" "$cache"
done
# Before the cross fix these imported targets referenced nonexistent /usr/pkg.
for var in PC_HARFBUZZ_INCLUDE_DIRS XKB_COMMON_X11_INCLUDE_DIRS; do
    dirs=$(awk -F= -v key="$var:INTERNAL" '$1==key { print $2 }' "$cache")
    [ -n "$dirs" ]
    saved_ifs=$IFS
    IFS=';'
    for dir in $dirs; do
        case "$dir" in "$sysroot"/*) ;; *) echo "Non-target include: $dir" >&2; exit 1;; esac
        [ -d "$dir" ]
    done
    IFS=$saved_ifs
done
"$host/libexec/moc" -v
"$scanner" --version
echo 'PASS: real Qt target configuration, native generators, sysroot includes and required Wayland/EGL features'
