#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross-build the original upstream API test.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 CROSS_TOOLS SYSROOT LIBPROXY_SOURCE NEW_WORK" >&2; exit 2; }
tools=$1 sysroot=$2 source=$3 work=$4
for path in "$tools" "$sysroot" "$source" "$work"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths' >&2; exit 2;; esac
done
mkdir "$work"
"$tools/bin/aarch64--netbsd-gcc" --sysroot="$sysroot" \
    -I"$source/src/libproxy" -I"$sysroot/usr/pkg/include/glib-2.0" \
    -I"$sysroot/usr/pkg/lib/glib-2.0/include" \
    -L"$sysroot/usr/pkg/lib" -L"$sysroot/usr/pkg/lib/libproxy" \
    -Wl,-rpath,/usr/pkg/lib -Wl,-rpath,/usr/pkg/lib/libproxy \
    -Wl,-rpath-link,"$sysroot/usr/pkg/lib" \
    -Wl,-rpath-link,"$sysroot/usr/pkg/lib/libproxy" \
    "$source/tests/libproxy-test.c" -lproxy -lgobject-2.0 -lglib-2.0 \
    -o "$work/test-libproxy"
file "$work/test-libproxy"
