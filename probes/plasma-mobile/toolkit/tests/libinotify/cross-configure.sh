#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Exercise the real generated configure script.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 CONFIGURED_SOURCE NEW_WORK" >&2; exit 2; }
source=$1 work=$2
: "${CC:?Set the target C compiler}"
: "${CXX:?Set the target C++ compiler}"
: "${BUILD_TRIPLET:?Set the native build triplet}"
: "${TARGET_TRIPLET:?Set the target triplet}"
case "$source:$work" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
mkdir "$work"
cp -R "$source" "$work/source"
# Remove only configure state from this disposable copy, preserving the input.
rm -f "$work/source/config.status" "$work/source/config.cache"
for check in ember_cv_note_extend_to ember_cv_note_extend_from ember_cv_o_path ember_cv_o_empty_path ember_cv_at_empty_path; do
    for value in '' invalid; do
        label=${value:-missing}
        run=$work/$check-$label
        mkdir "$run"
        if (cd "$run" && env ember_cv_note_extend_to=yes ember_cv_note_extend_from=no \
            ember_cv_o_path=no ember_cv_o_empty_path=no ember_cv_at_empty_path=no \
            "$check=$value" "$work/source/configure" --prefix=/usr/pkg \
            --build="$BUILD_TRIPLET" --host="$TARGET_TRIPLET") > "$run/configure.log" 2>&1; then
            echo "Unexpected configure success: $check=$value" >&2; exit 1
        fi
        grep -q "Set $check to a measured target result (yes or no)" "$run/configure.log"
    done
done
echo 'PASS: missing and invalid measurements rejected at all five cross-runtime probes'
