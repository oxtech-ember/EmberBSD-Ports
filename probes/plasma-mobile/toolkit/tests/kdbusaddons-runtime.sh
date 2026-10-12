#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), upstream installed D-Bus service tests.
set -eu
[ "$#" = 2 ] || { echo 'Usage: kdbusaddons-runtime.sh UPSTREAM_BINARIES NEW_OUTPUT' >&2; exit 2; }
binaries=$(CDPATH= cd -- "$1" && pwd)
for program in deadservicetest kdbusservicetest kdbussimpleservice; do
    [ -x "$binaries/$program" ]
done
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
umask 077
ulimit -c 0
mkdir "$work/home" "$work/runtime"
sysctl kern.boottime > "$work/boot.before"
pkg_info -e kf6-kdbusaddons > "$work/package.txt"
for program in deadservicetest kdbusservicetest kdbussimpleservice; do
    ldd "$binaries/$program" > "$work/$program.ldd"
    ! grep -q 'not found' "$work/$program.ldd"
    sha256 "$binaries/$program" >> "$work/inputs.sha256"
done
for program in deadservicetest kdbusservicetest; do
    result=0
    timeout -k 5 90 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 \
        XDG_RUNTIME_DIR="$work/runtime" QT_QPA_PLATFORM=minimal \
        dbus-run-session -- "$binaries/$program" > "$work/$program.log" 2>&1 || result=$?
    cat "$work/$program.log"
    [ "$result" = 0 ] || exit "$result"
done
# The custom service test also checks these with QT_FORCE_ASSERTS enabled.
grep -q 'Process exited with code 4' "$work/kdbusservicetest.log"
[ "$(grep -c 'Application executed with args' "$work/kdbusservicetest.log")" = 3 ]
grep -q 'Terminating.' "$work/kdbusservicetest.log"
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: installed D-Bus unique-instance activation and dead-service recovery on private buses'
