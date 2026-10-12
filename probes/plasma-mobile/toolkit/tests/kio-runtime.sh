#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), unchanged upstream installed KIO tests.
set -eu
[ "$#" = 2 ] || { echo 'Usage: kio-runtime.sh UPSTREAM_BINARIES NEW_OUTPUT' >&2; exit 2; }
binaries=$(CDPATH= cd -- "$1" && pwd)
programs='metadatatest upurltest globaltest kprotocolinfotest udsentrytest mkpathjobtest deletejobtest'
for program in $programs; do [ -x "$binaries/$program" ]; done
umask 077
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
ulimit -c 0
sysctl kern.boottime > "$work/boot.before"
pkg_info -e kf6-kio > "$work/package.txt"
failed=0
for program in $programs; do
    mkdir "$work/$program" "$work/$program/home" "$work/$program/runtime" "$work/$program/tmp"
    ldd "$binaries/$program" > "$work/$program/ldd.txt"
    ! grep -q 'not found' "$work/$program/ldd.txt"
    sha256 "$binaries/$program" >> "$work/inputs.sha256"
    result=0
    (
        cd "$work/$program"
        timeout -k 5 150 env -i PATH="$PATH" HOME="$PWD/home" LC_ALL=C.UTF-8 \
            XDG_RUNTIME_DIR="$PWD/runtime" TMPDIR="$PWD/tmp" QT_QPA_PLATFORM=minimal \
            dbus-run-session -- "$binaries/$program"
    ) > "$work/$program/test.log" 2>&1 || result=$?
    printf '%s\n' "$result" > "$work/$program/status"
    cat "$work/$program/test.log"
    [ "$result" = 0 ] || failed=1
done
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
[ "$failed" = 0 ] || exit 1
echo 'PASS: seven upstream KIO suites with installed libraries/workers and isolated temporary files'
