#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), focused upstream installed-library acceptance.
set -eu
[ "$#" = 2 ] || { echo 'Usage: libplasma-runtime.sh UPSTREAM_TEST_BUNDLE NEW_OUTPUT' >&2; exit 2; }
bundle=$(CDPATH= cd -- "$1" && pwd)
umask 077
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
ulimit -c 0
sysctl kern.boottime > "$work/boot.before"
pkg_info -e plasma6-libplasma > "$work/packages.txt"
pkg_info -e plasma6-plasma-activities >> "$work/packages.txt"
pkg_admin check plasma6-libplasma plasma6-plasma-activities > "$work/package-check.txt" 2>&1
for program in pluginloadertest themetest sharedqmlenginetest; do
    [ -x "$bundle/bin/$program" ]
    mkdir "$work/$program" "$work/$program/home" "$work/$program/runtime"
    ldd "$bundle/bin/$program" > "$work/$program/ldd.txt"
    ! grep -q 'not found' "$work/$program/ldd.txt"
    sha256 "$bundle/bin/$program" >> "$work/inputs.sha256"
    result=0
    (
        cd "$bundle"
        timeout -k 5 120 env -i PATH="$PATH" HOME="$work/$program/home" LC_ALL=C.UTF-8 \
            XDG_RUNTIME_DIR="$work/$program/runtime" QT_QPA_PLATFORM=offscreen \
            QT_QUICK_BACKEND=software dbus-run-session -- "$bundle/bin/$program"
    ) > "$work/$program/test.log" 2>&1 || result=$?
    printf '%s\n' "$result" > "$work/$program/status"
    cat "$work/$program/test.log"
    [ "$result" = 0 ] || exit "$result"
done
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: upstream plugin loading, theme data and shared QML engine; offscreen software checks, not GPU or full desktop acceptance'
