#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed upstream widget API tests.
set -eu
[ "$#" = 2 ] || { echo 'Usage: widgets-runtime.sh UPSTREAM_BINARIES NEW_OUTPUT' >&2; exit 2; }
binaries=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
umask 077
mkdir "$work/home" "$work/runtime"
sysctl kern.boottime > "$work/boot.before"
pkg_info -e kf6-kwidgetsaddons > "$work/package.txt"
for program in kdatecomboboxtest ktimecomboboxtest kdualactiontest kselectaction_unittest; do
    [ -x "$binaries/$program" ]
    ldd "$binaries/$program" > "$work/$program.ldd"
    ! grep -q 'not found' "$work/$program.ldd"
    grep -q '/usr/pkg/lib/libKF6WidgetsAddons' "$work/$program.ldd"
    sha256 "$binaries/$program" >> "$work/inputs.sha256"
    result=0
    timeout -k 5 120 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 TZ=UTC \
        XDG_RUNTIME_DIR="$work/runtime" QT_QPA_PLATFORM=minimal \
        "$binaries/$program" > "$work/$program.log" 2>&1 || result=$?
    cat "$work/$program.log"
    [ "$result" = 0 ] || exit "$result"
done
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: installed date/time and action widget APIs; physical input, GPU and Designer runtime remain separate'
