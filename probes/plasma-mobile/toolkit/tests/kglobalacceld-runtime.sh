#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), unchanged upstream accelerator service tests.
set -eu
[ "$#" = 2 ] || { echo 'Usage: kglobalacceld-runtime.sh UPSTREAM_BINARIES NEW_OUTPUT' >&2; exit 2; }
binaries=$(CDPATH= cd -- "$1" && pwd)
umask 077
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
ulimit -c 0
sysctl kern.boottime > "$work/boot.before"
pkg_info -e plasma6-kglobalacceld > "$work/package.txt"
for program in migrateconfigtest shortcutstest allowlisttest; do
    [ -x "$binaries/$program" ]
    mkdir "$work/$program" "$work/$program/home" "$work/$program/runtime"
    ldd "$binaries/$program" > "$work/$program/ldd.txt"
    ! grep -q 'not found' "$work/$program/ldd.txt"
    sha256 "$binaries/$program" >> "$work/inputs.sha256"
    result=0
    (
        cd "$work/$program"
        timeout -k 5 120 env -i PATH="$PATH" HOME="$PWD/home" LC_ALL=C.UTF-8 \
            XDG_RUNTIME_DIR="$PWD/runtime" QT_QPA_PLATFORM=minimal \
            dbus-run-session -- "$binaries/$program"
    ) > "$work/$program/test.log" 2>&1 || result=$?
    printf '%s\n' "$result" > "$work/$program/status"
    cat "$work/$program/test.log"
    [ "$result" = 0 ] || exit "$result"
done
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: upstream KGlobalAccelD migration, shortcuts and allowlist; dummy input backend, not physical keyboard input'
