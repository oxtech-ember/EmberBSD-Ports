#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed Breeze resource acceptance.
set -eu
[ "$#" = 2 ] || { echo 'Usage: breeze-resource-runtime.sh RESOURCE_TEST NEW_WORK' >&2; exit 2; }
program=$1
case "$program" in /*) ;; *) exit 2;; esac
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
umask 077
mkdir "$work/reference" "$work/empty" "$work/home"
ln -s /usr/pkg/share/icons/breeze "$work/reference/icons"
pkg_info -e 'breeze-icons>=6.31.0nb1' > "$work/package.txt"
sysctl kern.boottime > "$work/boot.before"
ldd "$program" > "$work/linkage.txt"
grep -q '/usr/pkg/lib/libKF6BreezeIcons' "$work/linkage.txt"
! grep -q 'not found' "$work/linkage.txt"
sha256 "$program" > "$work/input.sha256"
cd "$work/reference"
timeout -k 5 60 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 "$program" > "$work/resource.log" 2>&1
cd "$work/empty"
result=0
timeout -k 5 60 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 "$program" > "$work/missing-reference.log" 2>&1 || result=$?
[ "$result" = 1 ]
grep -q 'fsFile.open' "$work/missing-reference.log"
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
cat "$work/resource.log"
echo 'PASS: installed Breeze resource bytes match installed theme/icons; missing reference rejected'
