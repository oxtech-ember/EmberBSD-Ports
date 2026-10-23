#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the real Qt FFmpeg configure condition.
set -eu
[ "$#" = 2 ] || {
    echo "Usage: $0 VERIFIED_QTMULTIMEDIA_6_12_SOURCE NEW_OUTPUT" >&2
    exit 2
}
source=$1 out=$2
case "$source:$out" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
tests=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
recipe=${tests%/tests}
: "${CMAKE:=cmake}" "${PATCH:=patch}"
grep -Fq 'set(QT_REPO_MODULE_VERSION "6.12.0")' "$source/.cmake.conf"
mkdir "$out"
mkdir -p "$out/baseline/src/multimedia" "$out/patched/src/multimedia"
cp "$source/src/multimedia/configure.cmake" "$out/baseline/src/multimedia/configure.cmake"
cp "$source/src/multimedia/configure.cmake" "$out/patched/src/multimedia/configure.cmake"
patch_file=$recipe/patches/patch-src_multimedia_configure.cmake
(cd "$out/patched" && "$PATCH" --batch --forward --fuzz=0 -p0 < "$patch_file") > "$out/patch.log" 2>&1
if (cd "$out/patched" && "$PATCH" --batch --forward --fuzz=0 -p0 < "$patch_file") > "$out/repeat-patch.log" 2>&1; then
    echo 'FAIL: repeated patch was not rejected' >&2
    exit 1
fi
for mode in baseline patched; do
    awk '
        /^qt_feature\("ffmpeg" PRIVATE$/ { found++; active = 1 }
        active { print }
        active && /^\)$/ { active = 0 }
        END { if (found != 1 || active) exit 1 }
    ' "$out/$mode/src/multimedia/configure.cmake" > "$out/$mode-feature.cmake"
done
"$CMAKE" "-DBASELINE_FEATURE=$out/baseline-feature.cmake" \
    "-DPATCHED_FEATURE=$out/patched-feature.cmake" "-DOUTPUT=$out/conditions.tsv" \
    -P "$tests/ffmpeg-feature.cmake" > "$out/conditions.log" 2>&1
"$CMAKE" -E sha256sum "$source/src/multimedia/configure.cmake" \
    "$out/patched/src/multimedia/configure.cmake" "$patch_file" > "$out/inputs.sha256"
cat "$out/conditions.log"
echo 'No Qt library was built and no target program was executed.'
