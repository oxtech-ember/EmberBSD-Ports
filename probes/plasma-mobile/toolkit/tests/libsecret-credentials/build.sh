#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), compile the original failure and actual fix.
set -eu
[ "$#" = 5 ] || { echo 'Usage: build.sh TOOLS SYSROOT CONFIGURED_SOURCE ORIGINAL_ARCHIVE NEW_WORK' >&2; exit 2; }
tools=$1 sysroot=$2 source=$3 archive=$4 work=$5
for item in "$tools" "$sysroot" "$source" "$archive" "$work"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$item" in *[!a-zA-Z0-9_./+-]*) echo 'Unsupported path characters' >&2; exit 2;; esac
done
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = 142948339c5b971d8f6a8c7099521f6fd319b6fe73d2694b4e6d3310ed28b6e6 ]
mkdir "$work"
tar -xf "$archive" -C "$work" libsecret-0.21.8.2/egg/egg-unix-credentials.c libsecret-0.21.8.2/egg/egg-unix-credentials.h
cc=$tools/bin/aarch64--netbsd-gcc
set -- --sysroot="$sysroot" -B"$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/" -O2 -Wall -Wextra -Werror -I"$source/output" -I"$source/egg"
if "$cc" "$@" -c "$work/libsecret-0.21.8.2/egg/egg-unix-credentials.c" -o "$work/original.o" > "$work/original.log" 2>&1; then
    echo 'Original broken source unexpectedly compiled' >&2; exit 1
fi
grep -q 'set_local_creds' "$work/original.log"
grep -q 'fd.*undeclared' "$work/original.log"
owner=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# The upstream unused parameters are unrelated to the selected credential path.
"$cc" "$@" -Wno-unused-parameter "$source/egg/egg-unix-credentials.c" "$owner/main.c" -o "$work/credentials" > "$work/current.log" 2>&1
"$cc" "$@" -E "$source/egg/egg-unix-credentials.c" > "$work/current.i"
shasum -a 256 "$source/egg/egg-unix-credentials.c" "$source/output/config.h" "$archive" "$owner/main.c" "$work/credentials" > "$work/inputs-output.sha256"
echo 'PASS: original credential source fails; corrected actual source cross-links. Run credentials on EmberBSD.'
