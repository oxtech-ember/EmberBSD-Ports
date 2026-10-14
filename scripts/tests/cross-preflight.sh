#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Existing-work and archive-rejection regression.
set -eu
[ "$#" = 4 ] || { echo 'Usage: cross-preflight.sh GCC_PREFIX SYSROOT ARCHIVE_CACHE NEW_OUTPUT' >&2; exit 2; }
prefix=$1 sysroot=$2 cache=$3 out=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
umask 022
mkdir "$out"
for name in ruckig ffmpeg osqp libxml2; do
    case "$name" in
    ruckig) helper=$ports/probes/ruckig/cross-build.sh; archive=ruckig-0.19.4.tar.gz;;
    ffmpeg) helper=$ports/profiles/common-media/cross/build-ffmpeg-cpu.sh; archive=ffmpeg-9.0.2.tar.xz;;
    osqp) helper=$ports/probes/osqp/cross-build.sh; archive=osqp-1.0.0.tar.gz;;
    libxml2) helper=$ports/profiles/common-media/cross/build-libxml2.sh; archive=libxml2-2.15.4.tar.xz;;
    esac
    mkdir "$out/$name-protected"
    printf '%s\n' 'Preserve pre-existing work.' > "$out/$name-protected/SENTINEL"
    sha256sum "$out/$name-protected/SENTINEL" > "$out/$name-sentinel.sha256"
    cp "$cache/$archive" "$out/$name.bad"
    printf 'corrupt\n' >> "$out/$name.bad"
    for scenario in protected corrupt; do
        case "$scenario" in
        protected) input=$cache/$archive; output=$out/$name-protected;;
        corrupt) input=$out/$name.bad; output=$out/$name-output;;
        esac
        set -- sh "$helper" "$prefix" "$sysroot" "$input"
        if [ "$name" = osqp ]; then set -- "$@" "$cache/qdldl-0.1.9.tar.gz"; fi
        status=0
        "$@" "$output" > "$out/$name-$scenario.log" 2>&1 || status=$?
        [ "$status" -ne 0 ] && [ "$status" -lt 128 ] || exit 1
        printf '%s\n' "$status" > "$out/$name-$scenario.status"
        if [ "$scenario" = corrupt ]; then
            [ ! -e "$output" ] && [ ! -L "$output" ] || exit 1
            grep -q 'FAILED' "$out/$name-$scenario.log"
        else
            [ "$status" = 2 ]
            (cd "$output" && find . -print | LC_ALL=C sort) > "$out/$name-files.txt"
            printf '.\n./SENTINEL\n' > "$out/$name-expected.txt"
            cmp "$out/$name-files.txt" "$out/$name-expected.txt"
            sha256sum -c "$out/$name-sentinel.sha256"
        fi
    done
done
echo 'PASS: four existing work directories preserved and four corrupt archives rejected'
