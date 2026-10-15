#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Source this after setting profile, recipe and archive. No files are changed.
expected=$(awk -F '\t' '$1 == "gcc" && $2 == "16.2.0" {print $4}' "$profile/sources.tsv")
[ -f "$archive" ] && [ -n "$expected" ] && \
    [ "$(shasum -a 256 "$archive" | awk '{print $1}')" = "$expected" ] || {
    echo 'GCC archive SHA256 mismatch or missing archive.' >&2; exit 1;
}
# Use the same recorded patch set and RCS filtering as cross/build.sh.
patches=$(awk '/^SHA1 \(patch-/ && $2 != "(patch-isl_configure)" { gsub(/[()]/, "", $2); print $2 }' "$recipe/distinfo")
[ -n "$patches" ] || { echo 'No recipe patches.' >&2; exit 1; }
for name in $patches; do
    case "$name" in patch-*[!A-Za-z0-9_.-]*|*/*) echo 'Invalid patch name.' >&2; exit 1;; esac
    [ -f "$recipe/patches/$name" ] || { echo "Missing patch: $name" >&2; exit 1; }
    recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name {print $4}' "$recipe/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$recipe/patches/$name" | shasum -a 1 | awk '{print $1}')
    [ "$actual" = "$recorded" ] || { echo "Patch SHA1 mismatch: $name" >&2; exit 1; }
done
printf '%s\n' "$patches" | grep -qx patch-gcc_cp_module.cc || {
    echo 'The repaired GCC16 modules recipe is required.' >&2; exit 1;
}
# The target runtime ABI must agree with the owner recipe. Do not inherit
# upstream's .so.6 or NetBSD base's separate .so.9 process graph.
grep -F 's,libtool_VERSION=6:,libtool_VERSION=7:,g' "$recipe/Makefile" >/dev/null &&
    grep -F -- '--disable-libssp' "$recipe/Makefile" >/dev/null || {
    echo 'The exported recipe does not select the supported NetBSD runtime ABI.' >&2; exit 1;
}
