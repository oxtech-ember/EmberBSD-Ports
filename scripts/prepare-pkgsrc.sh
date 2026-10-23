#!/bin/sh
# Prepare a pinned pkgsrc tree with the EmberBSD recipes and infrastructure.
#
# The export has no profiles. It contains the pinned upstream pkgsrc tree,
# every recipe in the pkgsrc/ overlay, every recipe that pkgsrc/export.conf
# names, the infrastructure patches in pkgsrc/export.conf order and the
# exported files that pkgsrc/export.conf names.
set -eu
umask 022

[ "$#" -eq 1 ] || {
    echo 'Usage: sh scripts/prepare-pkgsrc.sh ABSOLUTE_NEW_DIRECTORY' >&2
    exit 2
}
destination=$1
case "$destination" in
    /*) ;;
    *) echo 'Destination must be absolute.' >&2; exit 2 ;;
esac
case "$destination" in
    *[!a-zA-Z0-9_./-]*) echo 'pkgsrc requires a path without whitespace or shell metacharacters.' >&2; exit 2 ;;
esac
[ ! -e "$destination" ] && [ ! -L "$destination" ] || { echo 'Destination already exists.' >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
config=$root/pkgsrc/export.conf
replaces=$root/pkgsrc/replaces
[ -f "$config" ] || { echo 'Missing pkgsrc/export.conf.' >&2; exit 2; }


fail() {
    echo "$*" >&2
    exit 2
}

# A recipe is complete when it has a Makefile, every patch that distinfo
# declares exists with the declared checksum, it has no undeclared patch,
# and every link resolves to a file in this repository.
check_recipe() {
    _source=$1
    _label=$2
    [ -f "$_source/Makefile" ] || fail "Incomplete recipe: $_label has no Makefile."
    if [ -f "$_source/distinfo" ]; then
        awk '$1 == "SHA1" && $2 ~ /^\(patch-/ { gsub(/[()]/, "", $2); print $2, $4 }' \
            "$_source/distinfo" > "$scratch/declared"
    else
        : > "$scratch/declared"
    fi
    while read -r _name _recorded; do
        [ -f "$_source/patches/$_name" ] || fail "Missing patch: $_label/patches/$_name"
        _computed=$(sed '/[$]NetBSD.*/d' "$_source/patches/$_name" | shasum -a 1 | awk '{ print $1 }')
        [ "$_recorded" = "$_computed" ] || fail "Patch checksum differs: $_label/patches/$_name"
    done < "$scratch/declared"
    if [ -d "$_source/patches" ]; then
        for _file in "$_source"/patches/patch-*; do
            [ -e "$_file" ] || [ -L "$_file" ] || continue
            awk -v name="${_file##*/}" '$1 == name { found = 1 } END { exit !found }' "$scratch/declared" ||
                fail "Undeclared patch: $_label/patches/${_file##*/}"
        done
    fi
    # A link must name a file in this repository with a relative path.
    find "$_source" -type l > "$scratch/links"
    while read -r _link; do
        _target=$(readlink "$_link")
        _relative=${_link#"$root"/}
        case "$_target" in
            /*) fail "Link leaves the repository: $_link" ;;
        esac
        printf '%s/%s\n' "${_relative%/*}" "$_target" | awk -F / '{
            depth = 0
            for (i = 1; i <= NF; i++) {
                if ($i == "..") { if (depth == 0) exit 1; depth-- }
                else if ($i != "." && $i != "") depth++
            }
        }' || fail "Link leaves the repository: $_link"
        [ -f "$_link" ] || fail "Broken link: $_link"
    done < "$scratch/links"
}

scratch=$(mktemp -d "${TMPDIR:-/tmp}/ember-pkgsrc.XXXXXXXX")
trap 'rm -rf "$scratch"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM

# Read pkgsrc/export.conf once. Check every input before the export.
tab=$(printf '\t')
: > "$scratch/recipes"
: > "$scratch/patches"
: > "$scratch/files"
while IFS="$tab" read -r method first second third extra; do
    case "$method" in ''|'#'*) continue ;; esac
    [ -z "$extra" ] || fail "pkgsrc/export.conf: too many fields for $method $first."
    case "$method" in
        recipe)
            [ -n "$second" ] && [ -z "$third" ] || fail "pkgsrc/export.conf: use recipe SOURCE PKGPATH."
            check_recipe "$root/$first" "$first"
            printf '%s\t%s\n' "$second" "$root/$first" >> "$scratch/recipes"
            ;;
        patch)
            [ -z "$second" ] || fail "pkgsrc/export.conf: use patch FILE."
            [ -s "$root/$first" ] || fail "Missing infrastructure patch: $first"
            printf '%s\t%s\t\t\n' "$method" "$first" >> "$scratch/patches"
            ;;
        git-apply)
            [ -n "$second" ] && [ -z "$third" ] || fail "pkgsrc/export.conf: use git-apply FILE MANIFEST."
            [ -s "$root/$first" ] || fail "Missing infrastructure patch: $first"
            recorded=$(awk -F "$tab" -v name="${first##*/}" '$1 == name { print $2 }' "$root/$second")
            computed=$(shasum -a 256 "$root/$first" | awk '{ print $1 }')
            [ -n "$recorded" ] && [ "$recorded" = "$computed" ] ||
                fail "Infrastructure patch differs from $second: $first"
            printf '%s\t%s\t\t\n' "$method" "$first" >> "$scratch/patches"
            ;;
        recipe-patch)
            [ -n "$third" ] || fail "pkgsrc/export.conf: use recipe-patch FILE PKGPATH NAME."
            [ -s "$root/$first" ] || fail "Missing recipe patch: $first"
            case "$third" in patch-*) ;; *) fail "Recipe patch names start with patch-: $third" ;; esac
            printf '%s\t%s\t%s\t%s\n' "$method" "$first" "$second" "$third" >> "$scratch/patches"
            ;;
        file)
            [ -n "$second" ] && [ -z "$third" ] || fail "pkgsrc/export.conf: use file SOURCE DESTINATION."
            [ -f "$root/$first" ] || fail "Missing exported file: $first"
            printf '%s\t%s\n' "$first" "$second" >> "$scratch/files"
            ;;
        *) fail "pkgsrc/export.conf: unknown method $method." ;;
    esac
done < "$config"

# Every overlay recipe is in the export.
for category in "$root"/pkgsrc/*; do
    [ -d "$category" ] || continue
    for package in "$category"/*; do
        [ -d "$package" ] || continue
        name=${category##*/}/${package##*/}
        check_recipe "$package" "pkgsrc/$name"
        printf '%s\t%s\n' "$name" "$package" >> "$scratch/recipes"
    done
done
duplicate=$(cut -f 1 "$scratch/recipes" | sort | uniq -d | head -n 1)
[ -z "$duplicate" ] || fail "Two recipe sources provide $duplicate."

expected=$(git -C "$root" ls-files --stage -- upstream/pkgsrc 2>/dev/null | awk '$1 == "160000" { print $2 }')
actual=$(git -C "$root/upstream/pkgsrc" rev-parse HEAD 2>/dev/null) || actual=
[ -n "$expected" ] && [ "$actual" = "$expected" ] ||
    fail 'Initialize the pinned submodule with git submodule update --init upstream/pkgsrc.'

git -C "$root/upstream/pkgsrc" archive --format=tar --output="$scratch/pkgsrc.tar" "$expected"
mkdir "$destination"
tar -xf "$scratch/pkgsrc.tar" -C "$destination"

# A recipe replaces an upstream recipe only if pkgsrc/replaces names it.
[ -f "$replaces" ] && grep -v '^#' "$replaces" | sed '/^$/d' > "$scratch/replaces" ||
    : > "$scratch/replaces"
while read -r recipe; do
    cut -f 1 "$scratch/recipes" | grep -qxF "$recipe" && [ -f "$destination/$recipe/Makefile" ] ||
        fail "pkgsrc/replaces names $recipe, but no EmberBSD recipe or no upstream recipe has it."
done < "$scratch/replaces"
while IFS="$tab" read -r recipe source; do
    if [ -e "$destination/$recipe" ] || [ -L "$destination/$recipe" ]; then
        grep -qxF "$recipe" "$scratch/replaces" ||
            fail "Upstream already has $recipe; add it to pkgsrc/replaces or remove it."
    fi
done < "$scratch/recipes"

# Install the recipes. A new overlay category is copied whole, with its
# category files.
: > "$scratch/new-categories"
for category in "$root"/pkgsrc/*; do
    [ -d "$category" ] || continue
    name=${category##*/}
    if [ ! -e "$destination/$name" ]; then
        cp -RL "$category" "$destination/$name"
        printf '%s\n' "$name" >> "$scratch/new-categories"
    elif [ -f "$category/Makefile" ]; then
        fail "Upstream already has $name; review the overlay."
    else
        for file in "$category"/*; do
            [ -d "$file" ] || fail "Unexpected overlay file: pkgsrc/$name/${file##*/}"
        done
    fi
done
while IFS="$tab" read -r recipe source; do
    case "$source" in
        "$root/pkgsrc/"*) ! grep -qxF "${recipe%%/*}" "$scratch/new-categories" || continue ;;
    esac
    rm -rf "$destination/$recipe"
    mkdir -p "$destination/${recipe%%/*}"
    cp -RL "$source" "$destination/$recipe"
done < "$scratch/recipes"

# Apply the infrastructure patches once, in order.
while IFS="$tab" read -r method file recipe name; do
    case "$method" in
        patch)
            patch -f -E -d "$destination" -p1 -F 0 < "$root/$file" ||
                fail "Infrastructure patch does not apply: $file"
            ;;
        git-apply)
            # A NetBSD source import with binary files.
            git -C "$destination" apply --check "$root/$file"
            git -C "$destination" apply "$root/$file"
            ;;
        recipe-patch)
            [ -d "$destination/$recipe/patches" ] || mkdir "$destination/$recipe/patches"
            [ ! -e "$destination/$recipe/patches/$name" ] ||
                fail "Recipe patch collision: $recipe/patches/$name"
            cp "$root/$file" "$destination/$recipe/patches/$name"
            sum=$(sed '/[$]NetBSD.*/d' "$root/$file" | shasum -a 1 | awk '{ print $1 }')
            printf 'SHA1 (%s) = %s\n' "$name" "$sum" >> "$destination/$recipe/distinfo"
            ;;
    esac
done < "$scratch/patches"

while IFS="$tab" read -r file target; do
    [ ! -e "$destination/$target" ] || fail "Exported file collision: $target"
    cp "$root/$file" "$destination/$target"
done < "$scratch/files"
printf '%s\n' "$expected" > "$destination/EMBERBSD-PKGSRC-REVISION"
