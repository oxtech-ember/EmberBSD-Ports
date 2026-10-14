#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), standard target pkgtools for a cross staging tree.
set -eu
test "$#" = 4 || { echo 'Usage: package-llama.sh STAGED_PREFIX RECIPE PACKAGE_OUTPUT BUILD_INFO' >&2; exit 2; }
stage=$1 recipe=$2 package=$3 info=$4
test "$(uname -s)" = NetBSD && test "$(uname -p)" = aarch64
for path do case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac; done
test -d "$stage/bin" && test -f "$recipe/PLIST" && test -f "$info"
test ! -e "$package" && test ! -L "$package"
test -f /usr/pkg/gcc16/lib/libstdc++.so.7
test -f /usr/pkg/gcc16/lib/libgcc_s.so.1
work=$(mktemp -d /tmp/llama-package.XXXXXXXX)
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
sed '/^@comment/d' "$recipe/PLIST" | LC_ALL=C sort > "$work/expected"
(cd "$stage" && find . -type f -print | sed 's|^\./||' | LC_ALL=C sort) > "$work/actual"
cmp "$work/expected" "$work/actual"
pkg_create -u root -g wheel -p "$stage" -I /usr/pkg \
    -c '-Local CPU language model inference and HTTP server' \
    -d "$recipe/DESCR" -f "$recipe/PLIST" -B "$info" "$package"
test -s "$package"
pkg_info -B "$package"
echo "Created target package: $package"
