#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; verify loaded target runtimes against the host SDK receipt.
set -eu
[ "$#" -eq 1 ] || { echo 'Usage: check-runtime.sh OUTPUT_DIRECTORY' >&2; exit 2; }
out=$1
family=$(cat "$out/compiler-family.txt")
case "$family" in
    clang) expected_roles='libcxx libcxxabi libunwind'; prefix=/usr/pkg/llvm ;;
    gcc) expected_roles='libstdc++ libgcc_s'; prefix=/usr/pkg/gcc16 ;;
    *) echo 'Invalid compiler family receipt.' >&2; exit 2 ;;
esac
awk -F '\t' 'NF != 3 || $1 == "" || $2 == "" || length($3) != 64 || $3 ~ /[^0-9a-f]/ { exit 1 }
    END { if (NR == 0) exit 1 }' "$out/runtime-files.tsv" || {
    echo 'Invalid runtime file receipt.' >&2; exit 2;
}
rows=$(wc -l < "$out/runtime-files.tsv" | tr -d ' ')
case "$family:$rows" in clang:3|gcc:2) ;; *) echo 'Unexpected runtime receipt rows.' >&2; exit 2;; esac
for role in $expected_roles; do
    row=$(awk -F '\t' -v role="$role" '$1 == role {print $2 "\t" $3}' "$out/runtime-files.tsv")
    [ "$(printf '%s\n' "$row" | wc -l | tr -d ' ')" -eq 1 ] || {
        echo "Missing or duplicate runtime receipt: $role" >&2; exit 2;
    }
    relative=${row%%"$(printf '\t')"*}
    expected=${row#*"$(printf '\t')"}
    case "$relative" in "$prefix"/*) ;; *) echo "Runtime path escapes selected prefix: $relative" >&2; exit 1;; esac
    expected_path=$(realpath "$relative")
    count=0
    while read -r marker loaded; do
        [ "$marker" = LOADED ] || continue
        actual=$(realpath "$loaded") || continue
        if [ "$actual" = "$expected_path" ]; then
            count=$((count + 1))
        fi
    done < "$out/loaded.txt"
    [ "$count" -eq 1 ] || { echo "Expected one loaded $role at $expected_path" >&2; exit 1; }
    if command -v sha256 >/dev/null 2>&1; then
        digest=$(sha256 -q "$expected_path")
    else
        digest=$(shasum -a 256 "$expected_path" | awk '{print $1}')
    fi
    [ "$digest" = "$expected" ] || { echo "Runtime SHA256 mismatch: $expected_path" >&2; exit 1; }
done
echo "PASS: loaded $family runtime files match selected SDK receipt"
