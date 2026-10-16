#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Run under an external timeout of 90 seconds. Preserve the actual test status.
set -eu
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "usage: $0 ABSOLUTE_CONSUMER NEW_ABSOLUTE_OUTPUT [PREFIX]" >&2
    exit 2
fi
consumer=$1
output=$2
prefix=${3:-/usr/pkg}
case "$consumer:$output:$prefix" in
    /*:/*:/*) ;;
    *) echo 'consumer, output and prefix must be absolute paths' >&2; exit 2 ;;
esac
test -x "$consumer"
test ! -e "$output"
umask 077
mkdir "$output"
mkdir "$output/home" "$output/config" "$output/cache"
PATH=/usr/sbin:/usr/bin:/sbin:/bin:$prefix/sbin:$prefix/bin
export PATH
pkg_info=${PKG_INFO:-pkg_info}
command -v "$pkg_info" > "$output/pkg-info-path.txt"
"$pkg_info" -q -e 'kf6-kcoreaddons-[0-9]*' > "$output/provider.txt"
env -i PATH="$PATH" LC_ALL=C ldd "$consumer" > "$output/ldd.txt"
sha256 "$consumer" "$prefix/lib/libKF6CoreAddons.so.6" > "$output/input-sha256.txt"
set +e
env -i PATH="$PATH" HOME="$output/home" XDG_CONFIG_HOME="$output/config" \
    XDG_CACHE_HOME="$output/cache" LC_ALL=C "$consumer" "$output" \
    > "$output/runtime.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$output/status"
cat "$output/runtime.log"
exit "$status"
