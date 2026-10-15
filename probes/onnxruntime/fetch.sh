#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 1 ] || { echo 'Usage: fetch.sh ARCHIVE_DIRECTORY' >&2; exit 2; }
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
mkdir -p "$1"
cache=$(CDPATH= cd "$1" && pwd)
hash()
{
    if command -v sha256 >/dev/null 2>&1; then sha256 -q "$1"; else shasum -a 256 "$1" | awk '{ print $1 }'; fi
}
# An existing archive must verify; it is never silently replaced.
cat "$recipe/sources.tsv" "$recipe/dependencies.tsv" | while read -r name expected url; do
    [ -n "$name" ] || continue
    if [ ! -f "$cache/$name" ]; then
        curl -fLsS --retry 2 --connect-timeout 20 --max-time 1200 "$url" -o "$cache/$name.part"
        [ "$(hash "$cache/$name.part")" = "$expected" ] || { echo "Checksum mismatch: $name" >&2; exit 1; }
        mv "$cache/$name.part" "$cache/$name"
    fi
    [ "$(hash "$cache/$name")" = "$expected" ] || { echo "Checksum mismatch: $name" >&2; exit 1; }
    printf 'Verified %s\n' "$name"
done
