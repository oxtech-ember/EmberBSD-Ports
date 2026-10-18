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
[ "$(digest "$archive")" = "$expected" ] || { echo 'KiCad archive SHA256 mismatch.' >&2; exit 2; }
# Extract the complete, pinned archive. Keep demos and QA input data.
mkdir "$source"
tar -xjf "$archive" --strip-components=1 -C "$source"
for delta in netbsd-platform.patch dxf-major-name.patch occt8-api.patch; do
    patch -f -F 0 -p1 -d "$source" -i "$here/patches/$delta"
done
for input in CMakeLists.txt qa/CMakeLists.txt demos/CMakeLists.txt api/CMakeLists.txt pcbnew/python/swig/pcbnew.i; do
    test -f "$source/$input"
done
printf '%s %s %s\n' "$name" "$expected" "$url" > "$source/.ember-source-pin"
printf 'Prepared complete KiCad 10.0.7 source: %s\n' "$source"
