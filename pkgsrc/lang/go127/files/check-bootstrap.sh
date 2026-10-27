#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted native bootstrap identity check.
set -eu
seed=$1
expected_os=$2
expected_arch=$3
pkg_admin=$4
if [ ! -x "$seed/bin/go" ]; then
    echo "Go bootstrap is not executable: $seed/bin/go" >&2
    exit 1
fi
# Go 1.27's make.bash requires Go 1.24.6 or newer. Clear persistent settings
# and prevent a seed from selecting or downloading another toolchain.
identity=$(GOROOT="$seed" GOENV=off GOTOOLCHAIN=local GOOS= GOARCH= \
    "$seed/bin/go" env GOVERSION GOHOSTOS GOHOSTARCH)
set -- $identity
if [ "$#" -ne 3 ] || [ "$2" != "$expected_os" ] || [ "$3" != "$expected_arch" ]; then
    echo "Go bootstrap must run natively on $expected_os/$expected_arch: $identity" >&2
    exit 1
fi
case "$1" in
    go*) version=${1#go} ;;
    *) echo "Go bootstrap has an unrecognized version: $1" >&2; exit 1 ;;
esac
if ! "$pkg_admin" pmatch 'go>=1.24.6' "go-$version"; then
    echo "Go bootstrap must be at least 1.24.6: $version" >&2
    exit 1
fi
printf 'Using native Go bootstrap %s (%s/%s)\n' "$version" "$2" "$3"
