#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Validate the toolkit recipe selection and canonical source ownership.
# The manifests select the recipes. RECIPES defaults to the pkgsrc/ overlay.
set -eu
mode=check
case "${1:-}" in --recipes|--sources|--inventory) mode=${1#--}; shift ;; esac
[ "$#" -eq 1 ] || [ "$#" -eq 2 ] ||
    { echo "Usage: $0 [--recipes|--sources|--inventory] TOOLKIT [RECIPES]" >&2; exit 2; }
toolkit=$(CDPATH= cd -- "$1" && pwd)
fail() { echo "$*" >&2; exit 2; }
recipes=${2:-$toolkit/../../../pkgsrc}
[ -d "$recipes" ] || fail "Missing recipe directory: $recipes"
recipes=$(CDPATH= cd -- "$recipes" && pwd)
for file in sources.tsv source-owners.tsv; do
    [ -f "$toolkit/$file" ] || fail "Missing toolkit manifest: $file"
done
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-toolkit-check.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
: > "$work/recipes"
awk -F '\t' '/^#/ || /^$/ { next } { print $1 }' "$toolkit/source-owners.tsv" "$toolkit/sources.tsv" |
    LC_ALL=C sort -u > "$work/recipes"
while IFS= read -r recipe; do
    case "$recipe" in
        */*/*|.*|*/.*|*[!a-zA-Z0-9_+./-]*) fail "Invalid toolkit recipe path: $recipe" ;;
    esac
    [ -d "$recipes/$recipe" ] && [ ! -L "$recipes/$recipe" ] || fail "Missing toolkit recipe: $recipe"
done < "$work/recipes"
# A recipe that uses a toolkit version selector or a shared source owner is a
# toolkit recipe. It must have a manifest row, or the checks below skip it.
{
    printf '%s\n' '"../../meta-pkgs/qt6/Makefile.common"' '"../../meta-pkgs/kde/kf6.mk"' \
        '"../../meta-pkgs/kde/plasma6.mk"' '"../../meta-pkgs/kde/applications.mk"'
    awk -F '\t' '!/^#/ && $3 == "meta" { print "\"../../" $2 "/Makefile.common\"" }' "$toolkit/source-owners.tsv"
} > "$work/selectors"
for makefile in "$recipes"/*/*/Makefile; do
    [ -f "$makefile" ] || continue
    recipe=${makefile#"$recipes/"}
    recipe=${recipe%/Makefile}
    grep -Eq '^[[:space:]]*\.[[:space:]]*include[[:space:]]' "$makefile" || continue
    sed -n 's/^[[:space:]]*\.[[:space:]]*include[[:space:]]*//p' "$makefile" |
        sed 's/[[:space:]]*$//' | grep -qxFf "$work/selectors" || continue
    grep -qxF "$recipe" "$work/recipes" || fail "Toolkit recipe has no manifest row: $recipe"
done
[ ! -d "$recipes/sysutils/ember-plasma-session" ] || grep -qxF sysutils/ember-plasma-session "$work/recipes" ||
    fail "Toolkit recipe has no manifest row: sysutils/ember-plasma-session"
awk -F '\t' -v inventory="$work/inventory" -v plan="$work/sources" '
    function fail(message) { print message > "/dev/stderr"; bad=1; exit 2 }
    function recipe(name) { return name ~ /^[a-z0-9][a-z0-9-]*\/[a-zA-Z0-9][a-zA-Z0-9_+.-]*$/ }
    function archive(name) { return name ~ /^[a-zA-Z0-9][a-zA-Z0-9._+-]*\.(tar\.(xz|gz|bz2|zst)|zip)$/ || name == "cxx-rust-cssparser-vendor-1.1.0-r1.tar" }
    function css_vendor(owner, name, hash, origin) {
        return owner == "devel/cxx-rust-cssparser" && name == "cxx-rust-cssparser-vendor-1.1.0-r1.tar" &&
            hash == "d2e42517a49923fcd79fb7f05b650a4821c218c4d04d9c9691c7fdef55e74a2a" && origin == "derived:cssparser-vendor-r1"
    }
    /^#/ || /^$/ { next }
    FILENAME == ARGV[1] {
        if (NF != 4 || !recipe($1) || !recipe($2) || ($3 != "package" && $3 != "meta" && $3 != "local") ||
            ($4 != "-" && !archive($4)) || mapped[$1]++) fail("Invalid source-owner entry: " $0)
        if ($3 == "local" && ($1 != "sysutils/ember-plasma-session" || $2 != $1 || $4 != "-"))
            fail("Invalid local source-owner binding: " $1)
        owner[$1]=$2; kind[$1]=$3
        if ($4 != "-") {
            if ($1 != $2) fail("Only a source owner can select a primary archive: " $1)
            primary[$1]=$4
        }
        next
    }
    FILENAME == ARGV[2] {
        derived=css_vendor($1, $2, $3, $4)
        if (NF != 4 || !recipe($1) || !archive($2) || length($3) != 64 || $3 !~ /^[0-9a-f]+$/ ||
            ($4 !~ /^https?:\/\/[^[:space:]]+$/ && !derived) ||
            (($2 == "cxx-rust-cssparser-vendor-1.1.0-r1.tar" || $4 ~ /^derived:/) && !derived) ||
            seen[$1 SUBSEP $2]++) fail("Invalid toolkit source entry: " $0)
        if (derived) css_derived=1
        source_hash[$1 SUBSEP $2]=$3; source_origin[$1 SUBSEP $2]=$4
        if (blob_owner[$2] && blob_owner[$2] != $1) fail("Archive must have one canonical owner: " $2)
        blob_owner[$2]=$1
        count[$1]++; first[$1]=$2
        source[++rows]=$0; source_owner[rows]=$1; source_archive[rows]=$2
        next
    }
    FILENAME == ARGV[3] {
        if (NF != 1 || !recipe($1) || exported[$1]++) fail("Invalid toolkit recipe path: " $0)
        names[++recipes]=$1
    }
    END {
        if (bad) exit 2
        if (!recipes || !rows) fail("Empty toolkit recipe or source manifest")
        if (css_derived && (owner["devel/cxx-rust-cssparser"] != "devel/cxx-rust-cssparser" ||
            kind["devel/cxx-rust-cssparser"] != "package" || primary["devel/cxx-rust-cssparser"] != "cxx-rust-cssparser-1.1.0.tar.gz" ||
            source_hash["devel/cxx-rust-cssparser" SUBSEP "cxx-rust-cssparser-1.1.0.tar.gz"] != "97bf4670e565bf43ae77348af74a38c1b432fc5dfa47ab15c375e04331fdb8e1" ||
            source_origin["devel/cxx-rust-cssparser" SUBSEP "cxx-rust-cssparser-1.1.0.tar.gz"] != "https://github.com/KDE/cxx-rust-cssparser/archive/refs/tags/v1.1.0.tar.gz"))
            fail("Derived CSS parser source binding mismatch")
        for (name in mapped) {
            if (!exported[name] || !exported[owner[name]]) fail("Unknown source-owner recipe: " name)
            if (owner[owner[name]] && owner[owner[name]] != owner[name]) fail("Source-owner chains are not supported: " name)
        }
        for (name in count) {
            if (!exported[name] || (owner[name] && owner[name] != name)) fail("Source manifest must name a canonical owner: " name)
            if (count[name] > 1 && !primary[name]) fail("Multiple archives require an explicit primary archive: " name)
            if (!primary[name]) primary[name]=first[name]
            if (!seen[name SUBSEP primary[name]]) fail("Primary archive is not in the source manifest: " name)
        }
        for (i=1; i<=recipes; i++) {
            name=names[i]; actual=owner[name] ? owner[name] : name
            if (kind[name] == "local") {
                if (count[actual]) fail("Local recipe must not select an archive: " name)
            } else if (!count[actual]) fail("Missing toolkit source owner: " name " -> " actual)
            print name "\t" actual "\t" (kind[name] ? kind[name] : "package") > inventory
        }
        for (i=1; i<=rows; i++)
            print source[i] "\t" (primary[source_owner[i]] == source_archive[i] ? "primary" : "auxiliary") > plan
    }
' "$toolkit/source-owners.tsv" "$toolkit/sources.tsv" "$work/recipes" || exit 2
# Shared consumers must inherit source metadata. This is a restricted static
# contract, not a general evaluator for arbitrary bmake source selection.
check_shared_reference() {
    awk -v owner="$owner" '
        {
            line=$0; sub(/[[:space:]]*#.*/, "", line)
            if (line ~ /^[[:space:]]*\.[[:space:]]*(if|ifdef|ifndef|ifmake|ifnmake|for)[[:space:]]/) depth++
            if (line ~ /^[[:space:]]*\.[[:space:]]*(endif|endfor)([[:space:]]|$)/) depth--
            if (!depth && line ~ /^[[:space:]]*\.[[:space:]]*include[[:space:]]+/) {
                sub(/^[[:space:]]*\.[[:space:]]*include[[:space:]]+/, "", line)
                sub(/[[:space:]]+$/, "", line)
                if (line == "\"../../" owner "/Makefile.common\"") found=1
            }
        }
        END { exit !found }
    ' "$1" || fail "Shared source owner is not referenced by an unconditional include: $recipe -> $owner"
}
check_shared_metadata() {
    for path in "$1/distinfo" "$1/patches"; do
        [ ! -e "$path" ] && [ ! -L "$path" ] || fail "Shared consumer has local source metadata: $recipe ($path)"
    done
    find "$1" -type f \( -name Makefile -o -name 'Makefile.*' -o -name '*.mk' \) -print > "$work/shared-makefiles"
    while IFS= read -r file; do
        awk '
            {
                line=$0; sub(/[[:space:]]*#.*/, "", line)
                if (line ~ /\\$/) { sub(/\\$/, "", line); pending=pending line " "; next }
                line=pending line; pending=""
                if (line ~ /^[[:space:]]*(DISTINFO_FILE|PATCHDIR)[[:space:]]*[:+?!]?=/ ||
                    (line ~ /^[[:space:]]*\.[[:space:]]*undef[[:space:]]/ &&
                     line ~ /(^|[[:space:]])(DISTINFO_FILE|PATCHDIR)([[:space:]]|$)/)) exit 1
            }
        ' "$file" || fail "Shared consumer overrides source metadata: $recipe ($file)"
    done < "$work/shared-makefiles"
}
while IFS="$(printf '\t')" read -r recipe owner kind; do
    pkg=$recipes/$recipe
    [ -f "$pkg/Makefile" ] || fail "Incomplete toolkit recipe: $recipe/Makefile"
    if [ "$kind" = meta ]; then
        grep -Eq '^META_PACKAGE[[:space:]]*=[[:space:]]*yes([[:space:]]*(#.*)?)?$' "$pkg/Makefile" ||
            fail "Metadata-only recipe must declare META_PACKAGE=yes: $recipe"
    else
        [ -f "$pkg/PLIST" ] || fail "Incomplete toolkit recipe: $recipe/PLIST"
    fi
    if [ "$kind" = local ]; then
        [ ! -L "$recipes/${recipe%%/*}" ] && [ ! -L "$pkg" ] && [ ! -L "$pkg/files" ] ||
            fail "External local source directory: $recipe"
        for path in "$pkg/distinfo" "$pkg/patches"; do
            [ ! -e "$path" ] && [ ! -L "$path" ] || fail "Local recipe has archive metadata: $recipe"
        done
        grep -Eq '^DISTFILES[[:space:]]*=[[:space:]]*(#.*)?$' "$pkg/Makefile" &&
            grep -Eq '^NO_BUILD[[:space:]]*=[[:space:]]*yes([[:space:]]*(#.*)?)?$' "$pkg/Makefile" ||
            fail "Local recipe must use empty DISTFILES and NO_BUILD=yes: $recipe"
        # The recipe owns the canonical service files. No link may replace them.
        [ "$(find "$pkg" -type l | wc -l | tr -d ' ')" = 0 ] ||
            fail "Missing or external canonical local source: $recipe"
        for name in plasma-service.pl ember_plasma.rc; do
            [ -f "$pkg/files/$name" ] || fail "Missing or external canonical local source: $recipe/$name"
        done
        [ "$(find "$pkg/files" ! -type d | wc -l | tr -d ' ')" = 2 ] || fail "Unexpected local source files: $recipe"
    fi
    if [ "$recipe" != "$owner" ]; then
        check_shared_reference "$pkg/Makefile"
        check_shared_metadata "$pkg"
        [ -f "$recipes/$owner/Makefile.common" ] || fail "Missing shared source include: $owner/Makefile.common"
    fi
done < "$work/inventory"
awk -F '\t' '!seen[$1]++ {print $1}' "$work/sources" > "$work/owners"
while IFS= read -r owner; do
    pkg=$recipes/$owner
    [ -f "$pkg/distinfo" ] || fail "Missing toolkit source metadata: $owner/distinfo"
    awk -v owner="$owner" '
        function fail(message) { print message > "/dev/stderr"; bad=1; exit 2 }
        FILENAME == ARGV[1] { if ($1 == owner) archive[$2]=1; next }
        /^BLAKE2s / || /^SHA512 / || /^Size / {
            if ($2 !~ /^\([^()]+\)$/) fail("Malformed distinfo digest: " owner "/" $2)
            name=$2; sub(/^\(/,"",name); sub(/\)$/,"",name)
            if (!archive[name] || found[$1 SUBSEP name]++) fail("Unexpected or duplicate distinfo source: " owner "/" name)
            if ($3 != "=") fail("Malformed distinfo digest: " owner "/" name)
            if ($1 == "Size") {
                if (NF != 5 || $4 !~ /^[0-9]+$/ || $4 == 0 || $5 != "bytes") fail("Invalid archive size: " owner "/" name)
            } else if (NF != 4 || $4 !~ /^[0-9a-f]+$/ || length($4) != ($1 == "SHA512" ? 128 : 64))
                fail("Invalid archive digest: " owner "/" name)
            next
        }
        /^SHA1 / {
            if ($2 !~ /^\([^()]+\)$/) fail("Malformed patch digest: " owner "/" $2)
            name=$2; sub(/^\(/,"",name); sub(/\)$/,"",name)
            if (NF != 4 || name !~ /^patch-[a-zA-Z0-9_.+-]+$/ || $3 != "=" || length($4) != 40 ||
                $4 !~ /^[0-9a-f]+$/ || patch[name]++) fail("Invalid patch digest: " owner "/" name)
            print name, $4
        }
        END {
            if (bad) exit 2
            for (name in archive)
                if (!found["BLAKE2s" SUBSEP name] || !found["SHA512" SUBSEP name] || !found["Size" SUBSEP name])
                    fail("Missing archive digest: " owner "/" name)
        }
    ' "$toolkit/sources.tsv" "$pkg/distinfo" > "$work/patches" || exit 2
    actual=0
    if [ -d "$pkg/patches" ]; then
        actual=$(find "$pkg/patches" -name 'patch-*' | wc -l | tr -d ' ')
    fi
    expected=$(wc -l < "$work/patches" | tr -d ' ')
    [ "$actual" = "$expected" ] || fail "Patch manifest differs: $owner"
    while read -r name expected; do
        [ -f "$pkg/patches/$name" ] || fail "Missing required patch: $owner/$name"
        actual=$(sed '/[$]NetBSD.*/d' "$pkg/patches/$name" | shasum -a 1 | awk '{print $1}')
        [ "$actual" = "$expected" ] || fail "Toolkit patch checksum differs: $owner/$name"
    done < "$work/patches"
done < "$work/owners"
case "$mode" in
    recipes) cat "$work/recipes" ;;
    inventory) cat "$work/inventory" ;;
    sources) cat "$work/sources" ;;
    check) echo 'PASS: toolkit recipe/source coverage, source ownership, archive metadata and patch checksums' ;;
esac
