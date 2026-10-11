#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run in a new isolated target directory.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 ABSOLUTE_BINARY NEW_WORK" >&2; exit 2; }
binary=$1 work=$2
case "$binary:$work" in /*:/*) ;; *) exit 2;; esac
umask 077
mkdir "$work"
mkdir "$work/home" "$work/config" "$work/cache"
export HOME="$work/home" XDG_CONFIG_HOME="$work/config" XDG_CACHE_HOME="$work/cache"
unset KDEHOME KDEROOTHOME
/usr/bin/timeout -k 3 10 "$binary" read 42 > "$work/default.log" 2>&1
/usr/bin/timeout -k 3 10 "$binary" write 17 > "$work/write.log" 2>&1
/usr/bin/timeout -k 3 10 "$binary" read 17 > "$work/restart.log" 2>&1
set +e
/usr/bin/timeout -k 3 10 "$binary" read 99 > "$work/wrong-value.log" 2>&1
status=$?
set -e
[ "$status" = 3 ]
grep -q '^Value=17$' "$work/config/ember-kconfig-test"
/usr/pkg/bin/kwriteconfig6 --file "$work/config/ember-kconfig-test" --group Test --key Value 23
/usr/bin/timeout -k 3 10 "$binary" read 23 > "$work/cli-write.log" 2>&1
[ "$(/usr/pkg/bin/kreadconfig6 --file "$work/config/ember-kconfig-test" --group Test --key Value)" = 23 ]
echo 'PASS: generated configuration defaults, persistence across processes, mismatch rejection and installed CLI interoperation'
