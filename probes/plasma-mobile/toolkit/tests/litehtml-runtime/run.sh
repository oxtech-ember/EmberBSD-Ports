#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 TEST_BINARY NEW_OUTPUT" >&2; exit 2; }
binary=$1 work=$2
case "$binary:$work" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
mkdir "$work"
uname -a > "$work/system.txt"
sysctl -n kern.boottime > "$work/boot-before.txt"
sha256 "$binary" > "$work/binary.sha256"
ldd "$binary" > "$work/ldd.txt"
timeout -k 5 60 "$binary" --gtest_output="xml:$work/results.xml" > "$work/tests.log" 2>&1
sysctl -n kern.boottime > "$work/boot-after.txt"
cmp "$work/boot-before.txt" "$work/boot-after.txt"
cat "$work/tests.log"
