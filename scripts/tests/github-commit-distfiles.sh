#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). mk/fetch/github.mk names the distfile of a
# commit-hash GITHUB_TAG ${DISTNAME}-${GITHUB_TAG}${EXTRACT_SUFX}, so a recipe
# whose DISTNAME lacks the hash must record that name in distinfo; otherwise
# the checksum step finds no entry and the build stops.
# Usage: github-commit-distfiles.sh [PKGSRC_OVERLAY]
set -eu
[ "$#" -le 1 ] || { echo 'Usage: github-commit-distfiles.sh [PKGSRC_OVERLAY]' >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
tree=${1:-$root/pkgsrc}
[ -d "$tree" ] || { echo "No recipe tree: $tree" >&2; exit 2; }
status=0
checked=0
for mk in "$tree"/*/*/Makefile; do
    tag=$(sed -n 's/^GITHUB_TAG=[[:space:]]*\([0-9a-f]\{7,\}\)[[:space:]]*$/\1/p' "$mk")
    [ -n "$tag" ] || continue
    grep -q '^DISTFILES[+?]*=' "$mk" && continue
    name=$(sed -n 's/^DISTNAME=[[:space:]]*\([^[:space:]]*\).*/\1/p' "$mk")
    case $name in ''|*'$'*|*"$tag"*) continue ;; esac
    sufx=$(sed -n 's/^EXTRACT_SUFX=[[:space:]]*\([^[:space:]]*\).*/\1/p' "$mk")
    file=$name-$tag${sufx:-.tar.gz}
    dir=$(dirname -- "$mk")
    checked=$((checked + 1))
    grep -Fq "($file) =" "$dir/distinfo" 2>/dev/null && continue
    echo "FAIL: ${dir#"$tree"/}/distinfo has no entry for $file" >&2
    status=1
done
[ "$status" -eq 0 ] || exit 1
echo "PASS: $checked commit-tag GitHub recipes record their tagged distfile"
