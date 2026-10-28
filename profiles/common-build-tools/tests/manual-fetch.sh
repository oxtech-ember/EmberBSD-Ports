#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Exercise the real pkgsrc fetch path with an explicitly selected manual mapping.
set -eu
[ "$#" = 5 ] || { echo 'usage: manual-fetch.sh BMAKE PKGSRC MAKECONF GZIP_ARCHIVE NEW_WORK' >&2; exit 2; }
bmake=$1 pkgsrc=$2 makeconf=$3 archive=$4 work=$5
for path in "$bmake" "$pkgsrc" "$makeconf" "$archive" "$work"; do
    case "$path" in /*) ;; *) echo 'absolute paths required' >&2; exit 2;; esac
done
mkdir "$work"
mkdir "$work/distfiles"
query() { "$bmake" -C "$pkgsrc/$1" MAKECONF="$makeconf" DISTDIR="$work/distfiles" "$2"; }
[ "$(query net/fetch '-V${FETCH_USING}')" = manual ]
query net/fetch fetch > "$work/fetch.log" 2>&1
query net/fetch checksum > "$work/checksum.log" 2>&1
cp "$archive" "$work/distfiles/gzip-1.15.tar"
query archivers/gzip fetch > "$work/cached-fetch.log" 2>&1
query archivers/gzip checksum > "$work/cached-checksum.log" 2>&1
printf 'corruption' >> "$work/distfiles/gzip-1.15.tar"
if query archivers/gzip checksum > "$work/corrupt.log" 2>&1; then
    echo 'manual mode accepted a corrupt cached archive' >&2; exit 1
fi
if query devel/py-mako fetch > "$work/missing.log" 2>&1; then
    echo 'manual mode accepted a missing distfile' >&2; exit 1
fi
grep -q 'Unable to fetch expected file' "$work/missing.log"
if "$bmake" -C "$pkgsrc/net/fetch" MAKECONF="$makeconf" FETCH_USING=fetch -V FETCH_USING > "$work/override.log" 2>&1; then
    echo 'manual mode accepted a fetch override' >&2; exit 1
fi
grep -q 'FETCH_USING differs from the selected fetch mode' "$work/override.log"
echo 'PASS: no-distfile and verified cached archive, corrupt or missing archive and override refusal'
