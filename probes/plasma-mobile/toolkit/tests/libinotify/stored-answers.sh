#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). A measured NetBSD 11.0 cross build of
# devel/libinotify must pass its stored target measurements to the real
# patched configure, which stops at its first runtime probe without them.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 PKGSRC MAKECONF TARGET_CC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 cc=$3 work=$4
case "$pkgsrc:$makeconf:$cc:$work" in /*:/*:/*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
: "${BMAKE:=bmake}"
pkg=$pkgsrc/devel/libinotify
q() { env MAKECONF="$makeconf" "$BMAKE" -C "$pkg" MAKECONF="$makeconf" -V "$1"; }
case $(q '${MACHINE_PLATFORM}:${USE_CROSS_COMPILE:tl}') in
    NetBSD-11.0-aarch64:yes) arch=aarch64 ;;
    NetBSD-11.0-x86_64:yes) arch=x86_64 ;;
    *) echo 'MAKECONF must select a measured NetBSD 11.0 cross target' >&2; exit 2 ;;
esac
answers=$(q '${CONFIGURE_ENV:Member_cv_*}')
for a in $answers; do
    case $a in ember_cv_*=yes|ember_cv_*=no) ;; *) echo "Invalid stored answer: $a" >&2; exit 1;; esac
done
mkdir "$work"
tar -xzf "$(q '${DISTDIR}/${DISTFILES}')" -C "$work"
src=$work/$(q '${WRKSRC:S,^${WRKDIR}/,,}')
(cd "$src" && "${PATCH:-nbpatch}" -p0 -s < "$pkg/patches/patch-configure.ac" && autoreconf -fi) > "$work/autoreconf.log" 2>&1
build=$(sh "$src/config.guess")
if ! (cd "$src" && env $answers CC="$cc" CXX="$cc --driver-mode=g++" \
    ./configure --build="$build" --host="$arch"--netbsd) > "$work/configure.log" 2>&1; then
    grep 'error:' "$work/configure.log" | tail -1 >&2
    echo 'FAIL: cross configure stopped' >&2; exit 1
fi
grep -q '^#define HAVE_NOTE_EXTEND_ON_MOVE_TO 1' "$src/config.h"
! grep -q '^#define HAVE_NOTE_EXTEND_ON_MOVE_FROM 1' "$src/config.h"
! grep -q '^#define HAVE_O_PATH 1' "$src/config.h"
echo 'PASS: stored NetBSD-11.0 target answers carry the cross configure'
