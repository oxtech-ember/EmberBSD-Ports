#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), every toolkit archive needs a Ports fetch site.
# A recipe without MASTER_SITES or SITES.<archive> can only try the generic
# distfile mirrors, which do not carry new upstream releases.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 TOOLKIT NEW_WORK" >&2; exit 2; }
toolkit=$(CDPATH= cd -- "$1" && pwd)
root=$(CDPATH= cd -- "$toolkit/../../.." && pwd)
overlay=$root/pkgsrc
upstream=$root/upstream/pkgsrc
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
${SH:-sh} "$toolkit/validate.sh" --sources "$toolkit" "$overlay" > "$work/source-plan.tsv"
# Print the recipe-owned make files reached from a file: framework includes
# such as kf6.mk count, dependency buildlink files and the mk/ tree do not.
resolve() {
    case "$1" in
        ../../*) rel=${1#../../} ;;
        *) rel=$2/$1 ;;
    esac
    if [ -f "$overlay/$rel" ]; then printf '%s\n' "$overlay/$rel"
    elif [ -f "$upstream/$rel" ]; then printf '%s\n' "$upstream/$rel"; fi
}
scan() {
    file=$1 dir=$2 depth=$3
    printf '%s\n' "$file"
    [ "$depth" -lt 3 ] || return 0
    sed -n 's/^\.[[:space:]]*include[[:space:]]*"\([^"]*\)".*/\1/p' "$file" |
    while IFS= read -r inc; do
        case "$inc" in
            ../../mk/*|*/buildlink3.mk|*/builtin.mk|*/options.mk|*/tools.mk|*/cross-tools.mk) continue ;;
        esac
        found=$(resolve "$inc" "$dir")
        [ -n "$found" ] || continue
        case "$inc" in ../../*) next=${inc#../../}; next=${next%/*} ;; *) next=$dir ;; esac
        scan "$found" "$next" $((depth + 1))
    done
}
: > "$work/missing.txt"
while IFS="$(printf '\t')" read -r recipe archive sha url role; do
    case "$recipe" in ''|'#'*) continue ;; esac
    makefile=$(resolve Makefile "$recipe")
    [ -n "$makefile" ] || { echo "Missing recipe: $recipe" >&2; exit 1; }
    scan "$makefile" "$recipe" 0 > "$work/files.txt"
    # shellcheck disable=SC2046
    if ! grep -Eq '^(MASTER_SITES|SITES\.[^=[:space:]]+)[?+]?=' $(cat "$work/files.txt"); then
        printf '%s\t%s\t%s\n' "$recipe" "$archive" "$url" >> "$work/missing.txt"
    fi
done < "$work/source-plan.tsv"
if [ -s "$work/missing.txt" ]; then
    echo 'Archives without a Ports fetch site:' >&2
    cat "$work/missing.txt" >&2
    exit 1
fi
echo 'PASS: every toolkit archive has a recipe fetch site'
