#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Exercise the production metadata validator and source verifier with tiny archives.
set -eu
[ "$#" -eq 1 ] || { echo "Usage: $0 NEW_WORK" >&2; exit 2; }
toolkit=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
fixture=$work/good
mkdir -p "$fixture/recipes" "$work/distfiles" "$work/archive/package" "$work/archive/dictionary"
printf 'before\n' > "$work/archive/package/value.txt"
printf 'dictionary payload\n' > "$work/archive/dictionary/words.txt"
tar -czf "$work/distfiles/code-1.tar.gz" -C "$work/archive" package
tar -czf "$work/distfiles/data-1.tar.gz" -C "$work/archive" dictionary
cp "$work/distfiles/code-1.tar.gz" "$work/distfiles/shared-1.tar.gz"
tar --zstd -cf "$work/distfiles/SDL3-1.tar.zst" -C "$work/archive" package
(cd "$work/archive" && zip -q "$work/distfiles/hunspell-en_US-1.zip" package/value.txt)
cp "$toolkit/validate.sh" "$fixture/validate.sh"
: > "$fixture/sources.tsv"
: > "$fixture/source-owners.tsv"
new_package() {
    mkdir -p "$fixture/recipes/$1"
    printf 'DISTNAME=fixture-1\n' > "$fixture/recipes/$1/Makefile"
    printf 'share/fixture\n' > "$fixture/recipes/$1/PLIST"
    printf '$NetBSD$\n\n' > "$fixture/recipes/$1/distinfo"
}
archive_row() {
    owner=$1
    archive=$2
    file=$work/distfiles/$archive
    sha=$(shasum -a 256 "$file" | awk '{print $1}')
    printf '%s\t%s\t%s\thttps://example.invalid/%s\n' "$owner" "$archive" "$sha" "$archive" >> "$fixture/sources.tsv"
    blake=$("${OPENSSL:-openssl}" dgst -blake2s256 "$file" | awk '{print $NF}')
    sha512=$(shasum -a 512 "$file" | awk '{print $1}')
    size=$(wc -c < "$file" | tr -d ' ')
    printf 'BLAKE2s (%s) = %s\nSHA512 (%s) = %s\nSize (%s) = %s bytes\n' \
        "$archive" "$blake" "$archive" "$sha512" "$archive" "$size" >> "$fixture/recipes/$owner/distinfo"
}
for recipe in devel/SDL3 textproc/hunspell-en_US devel/multi meta-pkgs/shared devel/first devel/second; do
    new_package "$recipe"
done
archive_row devel/SDL3 SDL3-1.tar.zst
archive_row textproc/hunspell-en_US hunspell-en_US-1.zip
# The auxiliary archive deliberately comes first. Its payload cannot take the code patch.
archive_row devel/multi data-1.tar.gz
archive_row devel/multi code-1.tar.gz
archive_row meta-pkgs/shared shared-1.tar.gz
printf 'META_PACKAGE=yes\nDISTFILES=\n' > "$fixture/recipes/meta-pkgs/shared/Makefile"
rm "$fixture/recipes/meta-pkgs/shared/PLIST"
cat > "$fixture/recipes/meta-pkgs/shared/Makefile.common" <<'COMMON'
DISTINFO_FILE=${.CURDIR}/../../meta-pkgs/shared/distinfo
PATCHDIR=${.CURDIR}/../../meta-pkgs/shared/patches
COMMON
for recipe in first second; do
    printf '.include "../../meta-pkgs/shared/Makefile.common"\n' > "$fixture/recipes/devel/$recipe/Makefile"
    rm "$fixture/recipes/devel/$recipe/distinfo"
done
cat > "$fixture/source-owners.tsv" <<'OWNERS'
devel/first	meta-pkgs/shared	package	-
devel/second	meta-pkgs/shared	package	-
meta-pkgs/shared	meta-pkgs/shared	meta	-
devel/multi	devel/multi	package	code-1.tar.gz
OWNERS
mkdir "$fixture/recipes/devel/multi/patches"
cat > "$fixture/recipes/devel/multi/patches/patch-value" <<'PATCH'
$NetBSD$

--- value.txt.orig
+++ value.txt
@@ -1 +1 @@
-before
+after
PATCH
patch_sha=$(sed '/[$]NetBSD.*/d' "$fixture/recipes/devel/multi/patches/patch-value" | shasum -a 1 | awk '{print $1}')
printf 'SHA1 (patch-value) = %s\n' "$patch_sha" >> "$fixture/recipes/devel/multi/distinfo"
sh "$toolkit/validate.sh" --inventory "$fixture" "$fixture/recipes" > "$work/inventory.tsv"
[ "$(wc -l < "$work/inventory.tsv" | tr -d ' ')" = 6 ]
sh "$toolkit/validate.sh" --sources "$fixture" "$fixture/recipes" > "$work/source-plan.tsv"
awk -F '\t' '$2=="data-1.tar.gz" {found=($5=="auxiliary")} END {exit !found}' "$work/source-plan.tsv"
sh "$toolkit/tests/verify-sources.sh" "$fixture" "$work/distfiles" "$work/verified" "$fixture/recipes" > "$work/verified.log" 2>&1
[ "$(cat "$work/verified/source/code-1/value.txt")" = after ]
[ ! -e "$work/verified/source/data-1" ]
[ "$(wc -l < "$work/verified/verified.tsv" | tr -d ' ')" = 5 ]
printf 'PASS: normal, multiarchive, shared-source and metadata-only contracts\n'
new_case() {
    name=$1
    candidate=$work/$name
    cp -R "$fixture" "$candidate"
}
expect_failure() {
    expected=$1
    if sh "$toolkit/validate.sh" "$candidate" "$candidate/recipes" > "$work/$name.log" 2>&1; then
        echo "Invalid fixture accepted: $name" >&2; exit 1
    fi
    grep -F "$expected" "$work/$name.log" >/dev/null || { cat "$work/$name.log" >&2; exit 1; }
    printf 'PASS: rejects %s\n' "$name"
}
new_case duplicate-source
head -1 "$candidate/sources.tsv" >> "$candidate/sources.tsv"
expect_failure 'Invalid toolkit source entry'
new_case duplicate-owner
head -1 "$candidate/source-owners.tsv" >> "$candidate/source-owners.tsv"
expect_failure 'Invalid source-owner entry'
new_case missing-primary
sed '/^devel\/multi/d' "$candidate/source-owners.tsv" > "$candidate/owners.new"
mv "$candidate/owners.new" "$candidate/source-owners.tsv"
expect_failure 'Multiple archives require an explicit primary archive'
new_case wrong-primary
sed 's/code-1.tar.gz/missing-1.tar.gz/' "$candidate/source-owners.tsv" > "$candidate/owners.new"
mv "$candidate/owners.new" "$candidate/source-owners.tsv"
expect_failure 'Primary archive is not in the source manifest'
new_case missing-auxiliary
sed '/data-1.tar.gz/d' "$candidate/sources.tsv" > "$candidate/sources.new"
mv "$candidate/sources.new" "$candidate/sources.tsv"
expect_failure 'Unexpected or duplicate distinfo source'
new_case missing-makefile
rm "$candidate/recipes/devel/SDL3/Makefile"
expect_failure 'Incomplete toolkit recipe'
new_case missing-plist
rm "$candidate/recipes/devel/SDL3/PLIST"
expect_failure 'Incomplete toolkit recipe'
new_case false-meta
printf 'DISTNAME=not-a-meta-package\n' > "$candidate/recipes/meta-pkgs/shared/Makefile"
expect_failure 'Metadata-only recipe must declare META_PACKAGE=yes'
new_case missing-owner-distinfo
rm "$candidate/recipes/meta-pkgs/shared/distinfo"
expect_failure 'Missing toolkit source metadata'
new_case unrelated-shared-owner
printf 'DISTNAME=unrelated\n' > "$candidate/recipes/devel/first/Makefile"
expect_failure 'Shared source owner is not referenced'
new_case commented-shared-owner
printf '# Old owner: ../../meta-pkgs/shared/Makefile.common\nDISTNAME=unrelated-9\n' > "$candidate/recipes/devel/first/Makefile"
expect_failure 'Shared source owner is not referenced by an unconditional include'
new_case conditional-shared-owner
printf '.if 0\n.include "../../meta-pkgs/shared/Makefile.common"\n.endif\n' > "$candidate/recipes/devel/first/Makefile"
expect_failure 'Shared source owner is not referenced by an unconditional include'
new_case ifmake-shared-owner
printf '.ifmake not_requested\n.include "../../meta-pkgs/shared/Makefile.common"\n.endif\n' > "$candidate/recipes/devel/first/Makefile"
expect_failure 'Shared source owner is not referenced by an unconditional include'
new_case ifnmake-shared-owner
printf '.ifnmake probe\n.include "../../meta-pkgs/shared/Makefile.common"\n.endif\n' > "$candidate/recipes/devel/first/Makefile"
expect_failure 'Shared source owner is not referenced by an unconditional include'
new_case overridden-shared-metadata
printf 'DISTINFO_FILE=${.CURDIR}/distinfo\nPATCHDIR=${.CURDIR}/patches\n' >> "$candidate/recipes/devel/first/Makefile"
printf 'Invalid source metadata\n' > "$candidate/recipes/devel/first/distinfo"
mkdir "$candidate/recipes/devel/first/patches"
printf 'Unlisted patch\n' > "$candidate/recipes/devel/first/patches/patch-unchecked"
expect_failure 'Shared consumer has local source metadata'
new_case shared-distinfo-override
printf 'DISTINFO_FILE=${.CURDIR}/other-digest\n' >> "$candidate/recipes/devel/first/Makefile"
expect_failure 'Shared consumer overrides source metadata'
new_case shared-patchdir-override
printf 'PATCHDIR:=/other/patches\n' > "$candidate/recipes/devel/first/options.mk"
expect_failure 'Shared consumer overrides source metadata'
new_case shared-continued-override
printf '%s\n' 'DISTINFO_FILE=\' ' ${.CURDIR}/other-digest' >> "$candidate/recipes/devel/first/Makefile"
expect_failure 'Shared consumer overrides source metadata'
new_case shared-undef-override
printf '.undef PATCHDIR\n' >> "$candidate/recipes/devel/first/Makefile"
expect_failure 'Shared consumer overrides source metadata'
new_case shared-local-patches
mkdir "$candidate/recipes/devel/first/patches"
printf 'Unlisted patch\n' > "$candidate/recipes/devel/first/patches/patch-unchecked"
expect_failure 'Shared consumer has local source metadata'
new_case missing-shared-include
rm "$candidate/recipes/meta-pkgs/shared/Makefile.common"
expect_failure 'Missing shared source include'
new_case unknown-owner
printf 'devel/absent\tmeta-pkgs/shared\tpackage\t-\n' >> "$candidate/source-owners.tsv"
expect_failure 'Missing toolkit recipe: devel/absent'
new_case unknown-shared-owner
printf 'devel/first\tmeta-pkgs/absent\tpackage\t-\n' > "$candidate/source-owners.new"
grep -v '^devel/first' "$candidate/source-owners.tsv" >> "$candidate/source-owners.new"
mv "$candidate/source-owners.new" "$candidate/source-owners.tsv"
expect_failure 'Unknown source-owner recipe'
new_case owner-chain
sed '1s|meta-pkgs/shared|devel/second|' "$candidate/source-owners.tsv" > "$candidate/owners.new"
mv "$candidate/owners.new" "$candidate/source-owners.tsv"
expect_failure 'Source-owner chains are not supported'
new_case unlisted-shared-consumer
mkdir -p "$candidate/recipes/devel/unlisted"
printf '.include "../../meta-pkgs/shared/Makefile.common"\n' > "$candidate/recipes/devel/unlisted/Makefile"
expect_failure 'Toolkit recipe has no manifest row: devel/unlisted'
new_case unlisted-version-selector
mkdir -p "$candidate/recipes/devel/kf6-unlisted"
printf '.include "../../meta-pkgs/kde/kf6.mk"\n' > "$candidate/recipes/devel/kf6-unlisted/Makefile"
expect_failure 'Toolkit recipe has no manifest row: devel/kf6-unlisted'
new_case recipe-without-archive
mkdir -p "$candidate/recipes/devel/orphan"
printf 'DISTNAME=orphan\n' > "$candidate/recipes/devel/orphan/Makefile"
printf 'share/orphan\n' > "$candidate/recipes/devel/orphan/PLIST"
printf 'devel/orphan\tdevel/orphan\tpackage\t-\n' >> "$candidate/source-owners.tsv"
expect_failure 'Missing toolkit source owner'
new_case malformed-sha256
sed '1s/[0-9a-f]\{64\}/bad/' "$candidate/sources.tsv" > "$candidate/sources.new"
mv "$candidate/sources.new" "$candidate/sources.tsv"
expect_failure 'Invalid toolkit source entry'
new_case missing-sha512
sed '/^SHA512 /d' "$candidate/recipes/devel/SDL3/distinfo" > "$candidate/digest.new"
mv "$candidate/digest.new" "$candidate/recipes/devel/SDL3/distinfo"
expect_failure 'Missing archive digest'
new_case malformed-size
sed 's/ bytes$/ widgets/' "$candidate/recipes/devel/SDL3/distinfo" > "$candidate/digest.new"
mv "$candidate/digest.new" "$candidate/recipes/devel/SDL3/distinfo"
expect_failure 'Invalid archive size'
new_case malformed-digest-name
sed 's/(SDL3-1.tar.zst)/SDL3-1.tar.zst/' "$candidate/recipes/devel/SDL3/distinfo" > "$candidate/digest.new"
mv "$candidate/digest.new" "$candidate/recipes/devel/SDL3/distinfo"
expect_failure 'Malformed distinfo digest'
new_case malformed-patch-name
sed 's/(patch-value)/patch-value/' "$candidate/recipes/devel/multi/distinfo" > "$candidate/digest.new"
mv "$candidate/digest.new" "$candidate/recipes/devel/multi/distinfo"
expect_failure 'Malformed patch digest'
new_case changed-patch
printf 'unexpected change\n' >> "$candidate/recipes/devel/multi/patches/patch-value"
expect_failure 'Toolkit patch checksum differs'
new_case missing-patch
rm "$candidate/recipes/devel/multi/patches/patch-value"
expect_failure 'Patch manifest differs'
new_case unlisted-patch
cp "$candidate/recipes/devel/multi/patches/patch-value" "$candidate/recipes/devel/multi/patches/patch-extra"
expect_failure 'Patch manifest differs'
new_case invalid-path
sed '1s|devel/SDL3|devel/../SDL3|' "$candidate/sources.tsv" > "$candidate/sources.new"
mv "$candidate/sources.new" "$candidate/sources.tsv"
expect_failure 'Invalid toolkit recipe path'
new_case invalid-url
sed '1s|https://|file:///|' "$candidate/sources.tsv" > "$candidate/sources.new"
mv "$candidate/sources.new" "$candidate/sources.tsv"
expect_failure 'Invalid toolkit source entry'
new_case invalid-recipe-path
printf 'devel/../escape\tmeta-pkgs/shared\tpackage\t-\n' >> "$candidate/source-owners.tsv"
expect_failure 'Invalid toolkit recipe path'
# The archive-verification entry point must enforce the same shared-owner gate.
for name in commented-shared-owner overridden-shared-metadata; do
    candidate=$work/$name
    if sh "$toolkit/tests/verify-sources.sh" "$candidate" "$work/distfiles" "$work/source-check-$name" "$candidate/recipes" > "$work/source-check-$name.log" 2>&1; then exit 1; fi
    case "$name" in
        commented-shared-owner) expected='Shared source owner is not referenced by an unconditional include' ;;
        overridden-shared-metadata) expected='Shared consumer has local source metadata' ;;
    esac
    grep -F "$expected" "$work/source-check-$name.log" >/dev/null
    printf 'PASS: source verification rejects %s\n' "$name"
done
# Actual archive verification must also reject a syntactically valid wrong hash.
new_case wrong-source-hash
sed '1s/[0-9a-f]\{64\}/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/' "$candidate/sources.tsv" > "$candidate/sources.new"
mv "$candidate/sources.new" "$candidate/sources.tsv"
if sh "$toolkit/tests/verify-sources.sh" "$candidate" "$work/distfiles" "$work/wrong-source-verification" "$candidate/recipes" > "$work/$name.log" 2>&1; then exit 1; fi
printf 'PASS: rejects wrong-source-hash during actual archive verification\n'
echo 'PASS: toolkit manifest regression complete'
