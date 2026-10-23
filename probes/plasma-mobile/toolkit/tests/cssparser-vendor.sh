#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Exercise the exact derived-source tuple and normal archive/patch checks.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 VERIFIED_DISTFILES NEW_WORK" >&2; exit 2; }
toolkit=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
recipes=$(CDPATH= cd -- "$toolkit/../../../pkgsrc" && pwd -P)
distfiles=$(CDPATH= cd -- "$1" && pwd -P)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd -P)
fixture=$work/good
owner=devel/cxx-rust-cssparser
original=cxx-rust-cssparser-1.1.0.tar.gz
vendor=cxx-rust-cssparser-vendor-1.1.0-r1.tar
source_sha=97bf4670e565bf43ae77348af74a38c1b432fc5dfa47ab15c375e04331fdb8e1
vendor_sha=d2e42517a49923fcd79fb7f05b650a4821c218c4d04d9c9691c7fdef55e74a2a
[ "$(shasum -a 256 "$distfiles/$original" | awk '{print $1}')" = "$source_sha" ]
[ "$(shasum -a 256 "$distfiles/$vendor" | awk '{print $1}')" = "$vendor_sha" ]
mkdir -p "$fixture/recipes/devel"
cp -R "$recipes/$owner" "$fixture/recipes/$owner"
cp "$toolkit/validate.sh" "$fixture/validate.sh"
printf '%s\t%s\tpackage\t%s\n' "$owner" "$owner" "$original" > "$fixture/source-owners.tsv"
printf '%s\t%s\t%s\thttps://github.com/KDE/cxx-rust-cssparser/archive/refs/tags/v1.1.0.tar.gz\n' "$owner" "$original" "$source_sha" > "$fixture/sources.tsv"
printf '%s\t%s\t%s\tderived:cssparser-vendor-r1\n' "$owner" "$vendor" "$vendor_sha" >> "$fixture/sources.tsv"
awk '/^SHA1 /' "$recipes/$owner/distinfo" > "$fixture/recipes/$owner/distinfo"
for archive in "$original" "$vendor"; do
    file=$distfiles/$archive
    printf 'BLAKE2s (%s) = %s\nSHA512 (%s) = %s\nSize (%s) = %s bytes\n' \
        "$archive" "$("${OPENSSL:-openssl}" dgst -blake2s256 "$file" | awk '{print $NF}')" \
        "$archive" "$(shasum -a 512 "$file" | awk '{print $1}')" \
        "$archive" "$(wc -c < "$file" | tr -d ' ')" >> "$fixture/recipes/$owner/distinfo"
done
sh "$toolkit/validate.sh" "$fixture" "$fixture/recipes"
sh "$toolkit/tests/verify-sources.sh" "$fixture" "$distfiles" "$work/verified" "$fixture/recipes"
grep -F "${vendor}$(printf '\t')${vendor_sha}$(printf '\t')derived:cssparser-vendor-r1$(printf '\t')auxiliary" "$work/verified/source-plan.tsv" >/dev/null
reject() {
    name=$1 pattern=$2 replacement=$3 file=$4
    candidate=$work/$name
    cp -R "$fixture" "$candidate"
    sed "s|$pattern|$replacement|g" "$candidate/$file" > "$candidate/new"
    mv "$candidate/new" "$candidate/$file"
    if sh "$toolkit/validate.sh" "$candidate" "$candidate/recipes" > "$work/$name.log" 2>&1; then
        echo "FAIL: accepted $name" >&2; exit 1
    fi
    printf 'PASS: rejects %s\n' "$name"
}
reject arbitrary-derived derived:cssparser-vendor-r1 derived:arbitrary sources.tsv
reject fake-http-derived derived:cssparser-vendor-r1 https://example.invalid/vendor sources.tsv
reject arbitrary-tar "$vendor" arbitrary.tar sources.tsv
reject changed-derived-hash "$vendor_sha" aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa sources.tsv
reject changed-source-binding "$source_sha" aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa sources.tsv
reject changed-upstream-url https://github.com/KDE/cxx-rust-cssparser/archive/refs/tags/v1.1.0.tar.gz https://example.invalid/source sources.tsv
reject derived-primary "$original" "$vendor" source-owners.tsv
reject foreign-owner "$owner" devel/foreign sources.tsv
candidate=$work/wrong-normal-digest
cp -R "$fixture" "$candidate"
sed '/^BLAKE2s (cxx-rust-cssparser-vendor-/s/= .*/= aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/' "$candidate/recipes/$owner/distinfo" > "$candidate/digest.new"
mv "$candidate/digest.new" "$candidate/recipes/$owner/distinfo"
if sh "$toolkit/tests/verify-sources.sh" "$candidate" "$distfiles" "$work/wrong-normal-digest-check" "$candidate/recipes" > "$work/wrong-normal-digest.log" 2>&1; then
    echo 'FAIL: accepted wrong normal BLAKE2s digest' >&2; exit 1
fi
grep -F BLAKE2s "$work/wrong-normal-digest.log" >/dev/null
mkdir "$work/changed-distfiles"
ln -s "$distfiles/$original" "$work/changed-distfiles/$original"
cp "$distfiles/$vendor" "$work/changed-distfiles/$vendor"
printf x >> "$work/changed-distfiles/$vendor"
if sh "$toolkit/tests/verify-sources.sh" "$fixture" "$work/changed-distfiles" "$work/changed-byte-check" "$fixture/recipes" > "$work/changed-byte.log" 2>&1; then
    echo 'FAIL: accepted changed derived archive bytes' >&2; exit 1
fi
if [ -n "${CSSPARSER_EXPORTED_PKGSRC:-}" ]; then
    native_make() {
        native_distfiles=$1; shift
        "${BMAKE:-bmake}" -C "$CSSPARSER_EXPORTED_PKGSRC/$owner" \
            "WRKOBJDIR=$work/make-objects" "DISTDIR=$native_distfiles" \
            PKG_BUILD_OPTIONS.qt6-qtbase= PKG_BUILD_OPTIONS.gcc16= "$@"
    }
    # Only source phases run. Empty cached option facts avoid unrelated native
    # dependency-option recursion; they do not establish Qt/compiler features.
    native_make "$distfiles" pre-fetch checksum-phase > "$work/native-checksum.log" 2>&1
    mkdir "$work/missing-distfiles"
    if native_make "$work/missing-distfiles" pre-fetch > "$work/native-missing.log" 2>&1; then
        echo 'FAIL: native pre-fetch accepted missing derived archive' >&2; exit 1
    fi
    grep -F "Prepare $vendor" "$work/native-missing.log" >/dev/null
    if native_make "$work/changed-distfiles" pre-fetch > "$work/native-changed.log" 2>&1; then
        echo 'FAIL: native pre-fetch accepted changed derived archive' >&2; exit 1
    fi
    grep -F 'Derived CSS parser vendor checksum mismatch' "$work/native-changed.log" >/dev/null
    if native_make "$work/changed-distfiles" checksum-phase > "$work/native-wrong-checksum.log" 2>&1; then
        echo 'FAIL: native checksum-phase accepted changed derived archive' >&2; exit 1
    fi
    grep -F 'Derived CSS parser vendor checksum mismatch' "$work/native-wrong-checksum.log" >/dev/null
    if native_make "$distfiles" "DISTINFO_FILE=$candidate/recipes/$owner/distinfo" checksum-phase > "$work/native-wrong-digest.log" 2>&1; then
        echo 'FAIL: native checksum-phase accepted wrong BLAKE2s metadata' >&2; exit 1
    fi
    grep -F BLAKE2s "$work/native-wrong-digest.log" >/dev/null
    echo 'PASS: actual exported recipe pre-fetch and checksum-phase; missing/changed derived bytes fail'
fi
echo 'PASS: exact derived CSS tuple, original source binding, normal checksums and zero-fuzz source patches'
