#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; compare loaded target runtimes with host-recorded SHA256.
set -eu
[ "$#" -eq 2 ] || { echo 'Usage: check-runtime.sh TARGET_PREFIX OUTPUT_DIRECTORY' >&2; exit 2; }
prefix=$(CDPATH= cd -- "$1" && pwd -P)
output=$2
for library in libstdc++.so libgcc_s.so; do
    expected=$(awk -F '\t' -v library="$library" '$1 == library { print $2 }' "$output/runtime-sha256.tsv")
    case "$expected" in ''|*[!0-9a-f]*) echo "Invalid runtime SHA256 receipt: $library" >&2; exit 1;; esac
    [ "${#expected}" -eq 64 ] || { echo "Invalid runtime SHA256 receipt: $library" >&2; exit 1; }
    awk -v library="$library" '$1 == "LOADED" && index($2, library) {print $2}' \
        "$output/loaded.txt" > "$output/$library.paths"
    [ "$(wc -l < "$output/$library.paths" | tr -d ' ')" -eq 1 ] || {
        echo "Expected one loaded $library" >&2; exit 1;
    }
    actual=$(realpath "$(cat "$output/$library.paths")")
    case "$actual" in "$prefix"/*) ;; *) echo "Runtime outside prefix: $actual" >&2; exit 1;; esac
    if command -v sha256 >/dev/null 2>&1; then
        digest=$(sha256 -q "$actual")
    else
        digest=$(shasum -a 256 "$actual" | awk '{print $1}')
    fi
    [ "$digest" = "$expected" ] || { echo "Runtime SHA256 mismatch: $actual" >&2; exit 1; }
done
