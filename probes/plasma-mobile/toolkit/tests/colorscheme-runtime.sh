#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), upstream installed color-scheme consumer.
set -eu
[ "$#" = 2 ] || { echo 'Usage: colorscheme-runtime.sh UPSTREAM_BINARY_AND_DATA NEW_OUTPUT' >&2; exit 2; }
binaries=$(CDPATH= cd -- "$1" && pwd)
[ -x "$binaries/kcolorschemetest" ] && [ -f "$binaries/kcolorschemetest.colors" ]
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
umask 077
mkdir "$work/home" "$work/runtime"
sysctl kern.boottime > "$work/boot.before"
pkg_info -e kf6-kcolorscheme > "$work/package.txt"
ldd "$binaries/kcolorschemetest" > "$work/libraries.txt"
sha256 "$binaries/kcolorschemetest" "$binaries/kcolorschemetest.colors" > "$work/inputs.sha256"
result=0
timeout -k 5 120 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 \
    XDG_RUNTIME_DIR="$work/runtime" QT_QPA_PLATFORM=minimal \
    "$binaries/kcolorschemetest" > "$work/test.log" 2>&1 || result=$?
cat "$work/test.log"
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
[ "$result" = 0 ] || exit "$result"
echo 'PASS: installed color schemes and contrast; no desktop latency claim'
