#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Package a verified cross staging prefix.
set -eu
umask 022
[ "$#" = 4 ] || { echo 'Usage: package-cross-stage.sh STAGED_PREFIX RECIPE OUTPUT BUILD_INFO' >&2; exit 2; }
stage=$1 recipe=$2 package=$3 info=$4
[ "$(uname -s)" = NetBSD ] || exit 1
machine_arch=$(uname -p)
case "$machine_arch" in aarch64|x86_64) ;; *) exit 1;; esac
for path do case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac; done
[ -d "$stage" ] && [ -f "$recipe/PLIST" ] && [ -f "$recipe/DESCR" ] && [ -f "$info" ] || exit 1
[ "$(sed -n 's/^MACHINE_ARCH=//p' "$info")" = "$machine_arch" ] || {
    echo 'Package metadata does not match this execution architecture.' >&2; exit 1;
}
[ ! -e "$package" ] && [ ! -L "$package" ] || { echo 'Output path already exists.' >&2; exit 2; }
work=$(mktemp -d /tmp/cross-package.XXXXXXXX)
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
sed '/^@comment/d' "$recipe/PLIST" | LC_ALL=C sort > "$work/expected"
(cd "$stage" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$work/actual"
cmp "$work/expected" "$work/actual"
# Store real package dependencies in +CONTENTS as well as build metadata.
depends=$(sed -n 's/^DEPENDS=//p' "$info")
case "$depends" in *[!A-Za-z0-9_.+\ -]*) echo 'Invalid exact package dependency list.' >&2; exit 2;; esac
pkg_create -u root -g wheel -p "$stage" -I /usr/pkg \
    -c '-EmberBSD cross-built package' -d "$recipe/DESCR" \
    -f "$recipe/PLIST" -B "$info" -P "$depends" "$package"
[ -s "$package" ]
pkg_info -B "$package"
