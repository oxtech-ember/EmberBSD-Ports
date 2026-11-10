#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 3 ] || { echo 'Usage: prepare-dependencies.sh DISTDIR NEW_MIRROR MANIFEST' >&2; exit 2; }
distdir=$1 mirror=$2 manifest=$3
mkdir "$mirror"
while read -r archive hash url; do
    case "$archive" in ''|'#'*) continue ;; esac
    case "$url" in https://*) ;; *) echo 'Expected an HTTPS dependency URL.' >&2; exit 2 ;; esac
    destination=$mirror/${url#https://}
    mkdir -p "$(dirname "$destination")"
    cp "$distdir/$archive" "$destination"
done < "$manifest"
