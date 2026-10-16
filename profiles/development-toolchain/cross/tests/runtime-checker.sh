#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted runtime receipt checks without target compilers.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
work=$(mktemp -d /tmp/ember-cross-runtime.XXXXXXXX)
work=$(CDPATH= cd -- "$work" && pwd -P)
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
mkdir -p "$work/prefix/lib" "$work/out"
printf 'selected C++ runtime\n' > "$work/prefix/lib/libstdc++.so.7.0"
printf 'selected GCC runtime\n' > "$work/prefix/lib/libgcc_s.so.1.0"
record() {
    printf 'libstdc++.so\t%s\n' "$(shasum -a 256 "$work/prefix/lib/libstdc++.so.7.0" | awk '{print $1}')"
    printf 'libgcc_s.so\t%s\n' "$(shasum -a 256 "$work/prefix/lib/libgcc_s.so.1.0" | awk '{print $1}')"
}
record > "$work/out/runtime-sha256.tsv"
printf 'LOADED %s\n' "$work/prefix/lib/libstdc++.so.7.0" "$work/prefix/lib/libgcc_s.so.1.0" > "$work/out/loaded.txt"
sh "$here/check-runtime.sh" "$work/prefix" "$work/out"
reject() {
    expected=$1
    if sh "$here/check-runtime.sh" "$work/prefix" "$work/out" > "$work/reject.log" 2>&1; then
        echo 'Accepted a foreign or damaged runtime.' >&2; exit 1
    fi
    grep -Fq "$expected" "$work/reject.log" || { cat "$work/reject.log" >&2; exit 1; }
}
printf 'corrupt\n' >> "$work/prefix/lib/libstdc++.so.7.0"
reject 'Runtime SHA256 mismatch:'
printf 'selected C++ runtime\n' > "$work/prefix/lib/libstdc++.so.7.0"
printf 'LOADED %s\n' "$work/prefix/lib/libstdc++.so.9" >> "$work/out/loaded.txt"
reject 'Expected one loaded libstdc++.so'
sed '$d' "$work/out/loaded.txt" > "$work/loaded"
mv "$work/loaded" "$work/out/loaded.txt"
cp "$work/prefix/lib/libstdc++.so.7.0" "$work/foreign-libstdc++.so.7.0"
printf 'LOADED %s\n' "$work/foreign-libstdc++.so.7.0" "$work/prefix/lib/libgcc_s.so.1.0" > "$work/out/loaded.txt"
reject 'Runtime outside prefix:'
printf 'LOADED %s\n' "$work/prefix/lib/libstdc++.so.7.0" "$work/prefix/lib/libgcc_s.so.1.0" > "$work/out/loaded.txt"
printf 'libstdc++.so\tbad\n' > "$work/out/runtime-sha256.tsv"
reject 'Invalid runtime SHA256 receipt:'
echo 'PASS: exact cross-runtime receipts, corruption, foreign paths and duplicate runtime rejection; no target compiler'
