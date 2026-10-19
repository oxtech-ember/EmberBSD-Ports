#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted native sanitizer consumer.
set -eu
[ "$#" = 3 ] || { echo 'Usage: native-check.sh CXX SOURCE_DIR NEW_OUTPUT' >&2; exit 2; }
cxx=$1 source=$2 out=$3
for path in "$source" "$out"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ -n "${TMPDIR:-}" ] || { echo 'Set TMPDIR to a task-specific absolute path.' >&2; exit 2; }
case "$TMPDIR" in /*) ;; *) echo 'TMPDIR must be absolute.' >&2; exit 2;; esac
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out" "$TMPDIR"
df -Pk "$out" > "$out/space-before.txt"
printf 'output=%s\nTMPDIR=%s\n' "$out" "$TMPDIR" > "$out/paths.txt"
"$cxx" --version > "$out/compiler.txt"
"$cxx" -std=c++17 -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I "$source/include" "$source/src/format.cc" \
    "$ports/probes/fmtlib/tests/formatting.cc" -o "$out/fmtlib-native"
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 "$out/fmtlib-native"
shasum -a 256 "$out/fmtlib-native" > "$out/output.sha256"
df -Pk "$out" > "$out/space-after.txt"
echo "PASS: native fmt 12.2.0 ASan/UBSan consumer: $out/fmtlib-native"
