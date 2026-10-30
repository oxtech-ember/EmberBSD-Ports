#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Check bytes before execution.
set -eu
[ "$#" = 3 ] || [ "$#" = 4 ] || { echo 'Usage: verify-mesa-generators.sh DIGEST SEALED_TOOLS MESA_SOURCE [intel|powervr|intel,powervr]' >&2; exit 2; }
digest=$1 tools=$2 source=$3 requested=${4-powervr}
fail() { echo "Mesa generator receipt: $*" >&2; exit 1; }
[ -x "$digest" ] && [ -d "$tools" ] && [ -d "$source" ] || fail 'missing input'
format=$(cat "$tools/FORMAT")
case "$format" in
    ember-mesa-generators-1) legacy=yes;;
    ember-mesa-generators-2)
        legacy=no
        [ -r "$tools/HOST" ] || fail 'missing host ABI record'
        host=$(cat "$tools/HOST")
        case "$host" in
            Darwin/arm64/clang|Darwin/arm64/gcc)
                [ "$(uname -s)" = Darwin ] || fail 'sealed generator host OS differs from build host'
                case "$(uname -m)" in arm64|aarch64) ;; *) fail 'sealed generator host CPU differs from build host';; esac;;
            Linux/x86_64/clang)
                [ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || fail 'sealed generator host ABI differs from build host';;
            *) fail 'unsupported sealed generator host ABI';;
        esac;;
    *) fail 'wrong format';;
esac
[ "$(cat "$source/VERSION")" = 26.2.6 ] || fail 'wrong source version'
case "$requested" in intel|powervr|intel,powervr) ;; *) fail 'unsupported generator profile';; esac
profiles=powervr
if [ -f "$tools/PROFILES" ]; then profiles=$(cat "$tools/PROFILES"); fi
case "$profiles" in intel|powervr|intel,powervr) ;; *) fail 'unsupported sealed profiles';; esac
case "$requested" in intel|intel,powervr)
    case ",$profiles," in *,intel,*) ;; *) fail 'seal does not supply Intel generators';; esac;;
esac
case "$requested" in powervr|intel,powervr)
    case ",$profiles," in *,powervr,*) ;; *) fail 'seal does not supply PowerVR generators';; esac;;
esac
required='mesa_clc vtn_bindgen2'
case "$requested" in powervr|intel,powervr) required="$required pco_clc";; esac

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
names="FORMAT HOST receipt.json interface.sha256"
if [ "$legacy" = yes ]; then names="FORMAT receipt.json interface.sha256"; fi
[ ! -f "$tools/PROFILES" ] || names="$names PROFILES"
for program in $required; do names="$names bin/$program"; done
for name in $names; do
    [ "$(awk -v name="$name" '$2 == name { n++ } END { print n+0 }' "$tools/installed.sha256")" = 1 ] || fail "missing or duplicate receipt entry: $name"
done
for name in $required; do
    [ -x "$tools/bin/$name" ] || fail "not executable: $name"
done
[ "$(awk '$2 == "src/util/u_dynarray.h" { n++ } END { print n+0 }' "$tools/interface.sha256")" = 1 ] || fail 'missing or duplicate shared generator source: src/util/u_dynarray.h'
verify "$source" "$tools/interface.sha256"
echo 'PASS: Mesa 26.2.6 native generator bytes and target interfaces'
