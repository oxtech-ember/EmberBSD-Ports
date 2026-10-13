#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Check bytes before execution.
set -eu
[ "$#" = 3 ] || { echo 'Usage: verify-mesa-generators.sh DIGEST SEALED_TOOLS MESA_SOURCE' >&2; exit 2; }
digest=$1 tools=$2 source=$3
fail() { echo "Mesa generator receipt: $*" >&2; exit 1; }
[ -x "$digest" ] && [ -d "$tools" ] && [ -d "$source" ] || fail 'missing input'
[ "$(cat "$tools/FORMAT")" = ember-mesa-generators-1 ] || fail 'wrong format'
[ "$(cat "$source/VERSION")" = 26.2.4 ] || fail 'wrong source version'
verify() {
    root=$1 manifest=$2
    [ -s "$manifest" ] || fail 'empty manifest'
    count=0
    while read -r expected file extra || [ -n "$expected$file$extra" ]; do
        [ "${#expected}" = 64 ] && [ -n "$file" ] && [ -z "$extra" ] || fail 'invalid manifest row'
        case "$expected" in *[!0-9a-f]*) fail 'invalid SHA256';; esac
        case "$file" in /*|*[!A-Za-z0-9_./-]*|'') fail 'unsafe path';; esac
        case "/$file/" in */../*|*/./*) fail 'unsafe path component';; esac
        [ -f "$root/$file" ] && [ ! -L "$root/$file" ] || fail "missing regular file: $file"
        actual=$("$digest" SHA256 "$root/$file") || fail "cannot hash: $file"
        [ "${actual##* }" = "$expected" ] || fail "changed file: $file"
        count=$((count + 1))
    done < "$manifest"
    [ "$count" -gt 0 ] || fail 'empty manifest'
}
verify "$tools" "$tools/installed.sha256"
for name in FORMAT receipt.json interface.sha256 bin/mesa_clc bin/vtn_bindgen2 bin/pco_clc; do
    [ "$(awk -v name="$name" '$2 == name { n++ } END { print n+0 }' "$tools/installed.sha256")" = 1 ] || fail "missing or duplicate receipt entry: $name"
done
for name in mesa_clc vtn_bindgen2 pco_clc; do
    [ -x "$tools/bin/$name" ] || fail "not executable: $name"
done
verify "$source" "$tools/interface.sha256"
echo 'PASS: Mesa 26.2.4 native generator bytes and target interfaces'
