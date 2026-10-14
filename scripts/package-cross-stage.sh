#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Package a verified cross staging prefix.
set -eu
umask 022
[ "$#" = 4 ] || { echo 'Usage: package-cross-stage.sh STAGED_PREFIX RECIPE OUTPUT BUILD_INFO' >&2; exit 2; }
stage=$1 recipe=$2 package=$3 info=$4
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = aarch64 ]
for path do case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac; done
[ -d "$stage" ] && [ -f "$recipe/PLIST" ] && [ -f "$recipe/DESCR" ] && [ -f "$info" ]
[ ! -e "$package" ] && [ ! -L "$package" ]
work=$(mktemp -d /tmp/cross-package.XXXXXXXX)
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
sed '/^@comment/d' "$recipe/PLIST" | LC_ALL=C sort > "$work/expected"
(cd "$stage" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$work/actual"
cmp "$work/expected" "$work/actual"
pkg_create -u root -g wheel -p "$stage" -I /usr/pkg \
    -c '-EmberBSD cross-built package' -d "$recipe/DESCR" \
    -f "$recipe/PLIST" -B "$info" "$package"
[ -s "$package" ]
pkg_info -B "$package"
