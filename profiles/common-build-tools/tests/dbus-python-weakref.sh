#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). dbus-python compiles against Python 3.15,
# which removed PyWeakref_GetObject.
# Usage: dbus-python-weakref.sh CC SYSROOT SOURCE [PATCH]
# CC is the target C compiler, SYSROOT has the target Python 3.15 and D-Bus
# headers, SOURCE is an extracted dbus-python-1.3.2. With PATCH, the test
# applies it (PATCH_TOOL, default patch) to a copy of SOURCE first.
set -eu
[ $# -ge 3 ] || { echo 'usage: dbus-python-weakref.sh CC SYSROOT SOURCE [PATCH]' >&2; exit 2; }
cc=$1 sysroot=$2 source=$3 patchfile=${4:-}
work=$(mktemp -d "${TMPDIR:-/tmp}/dbus-python-weakref.XXXXXX")
trap 'rm -rf "$work"' EXIT
cp -R "$source" "$work/src"
if [ -n "$patchfile" ]; then
    (cd "$work/src" && "${PATCH_TOOL:-patch}" -p0 -s < "$patchfile")
fi
: > "$work/config.h"
for f in conn.c server.c; do
    "$cc" -fsyntax-only -std=c99 -Werror=implicit-function-declaration \
        -Werror=int-conversion -include "$work/config.h" \
        -I"$work/src/include" -I"$work/src/dbus_bindings" \
        -I"$sysroot/usr/pkg/include/python3.15" \
        -I"$sysroot/usr/pkg/include/dbus-1.0" \
        -I"$sysroot/usr/pkg/lib/dbus-1.0/include" \
        "$work/src/dbus_bindings/$f" 2> "$work/err" || {
        cat "$work/err" >&2
        echo "FAIL: dbus_bindings/$f does not compile against Python 3.15" >&2
        exit 1
    }
done
echo 'PASS: dbus-python compiles against Python 3.15 weak reference API'
