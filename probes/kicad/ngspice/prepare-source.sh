#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
set -eu
umask 022
[ "$#" = 2 ] || { echo 'Usage: prepare-source.sh ABS_ARCHIVE ABS_NEW_SOURCE' >&2; exit 2; }
archive=$1
source=$2
for path in "$archive" "$source"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2 ;; esac
done
[ -f "$archive" ] || { echo 'Archive is missing.' >&2; exit 2; }
[ ! -e "$source" ] && [ ! -L "$source" ] || { echo 'Source path already exists.' >&2; exit 2; }
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for tool in tar patch; do command -v "$tool" >/dev/null; done
if command -v sha256sum >/dev/null; then
    digest() { sha256sum "$1" | cut -d ' ' -f 1; }
elif command -v sha256 >/dev/null; then
    digest() { sha256 -q "$1"; }
else
    command -v shasum >/dev/null
    digest() { shasum -a 256 "$1" | cut -d ' ' -f 1; }
fi
read -r name expected url < "$here/sources.tsv"
[ "$(digest "$archive")" = "$expected" ] || { echo 'ngspice archive SHA256 mismatch.' >&2; exit 2; }
mkdir "$source"
tar -xzf "$archive" --strip-components=1 -C "$source"
while IFS= read -r delta; do
    case "$delta" in ''|*[!a-z0-9.-]*) echo 'Invalid patch name.' >&2; exit 2 ;; esac
    patch -f -F 0 -p1 -d "$source" -i "$here/patches/$delta"
done < "$here/patches/series"
for input in COPYING configure.ac src/include/ngspice/sharedspice.h src/xspice/icm/GNUmakefile.in src/ciderlib/Makefile.am; do
    test -f "$source/$input"
done
printf '%s %s %s\n' "$name" "$expected" "$url" > "$source/.ember-source-pin"
printf 'Prepared complete ngspice 47 source: %s\n' "$source"
