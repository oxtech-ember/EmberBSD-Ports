#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Check publication inputs for the complete recipe layers in pkgsrc/ and
# pkgsrc/export.conf.
set -eu
[ "$#" -le 1 ] || { echo "Usage: $0 [PORTS_REPOSITORY]" >&2; exit 2; }
root=${1:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
root=$(CDPATH= cd -- "$root" && pwd)
[ "$(git -C "$root" rev-parse --show-toplevel)" = "$root" ] || {
    echo 'The argument must be the Ports repository root.' >&2; exit 2;
}
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-published-patches.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
# Sparse profiles outside the export have a different ownership contract.
git -C "$root" -c core.quotePath=false ls-files -- \
    pkgsrc profiles/common-build-tools/recipes \
    profiles/common-graphics/recipes > "$work/tracked"
: > "$work/references"
count=0
while IFS= read -r path; do
    case "$path" in */distinfo) ;; *) continue ;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo "Unsupported metadata path: $path" >&2; exit 2 ;; esac
    [ -f "$root/$path" ] || { echo "Missing tracked source metadata: $path" >&2; exit 1; }
    count=$((count + 1))
    awk -v directory="${path%/distinfo}/patches/" '
        /^SHA1 \(patch-/ {
            if (NF != 4 || $2 !~ /^\(patch-[a-zA-Z0-9_.+-]+\)$/ || $3 != "=" ||
                length($4) != 40 || $4 !~ /^[0-9a-f]+$/) exit 2
            name=$2; sub(/^\(/, "", name); sub(/\)$/, "", name)
            print directory name
        }
    ' "$root/$path" >> "$work/references"
done < "$work/tracked"
[ "$count" -gt 0 ] || { echo 'No complete recipe source metadata is tracked.' >&2; exit 1; }
awk '
    FILENAME == ARGV[1] { tracked[$0]=1; next }
    !tracked[$0] { print "Declared patch is not tracked by Git: " $0 > "/dev/stderr"; bad=1 }
    END { exit bad }
' "$work/tracked" "$work/references"
while IFS= read -r path; do
    [ -f "$root/$path" ] || { echo "Missing declared patch: $path" >&2; exit 1; }
done < "$work/references"
printf 'PASS: declared patches are tracked for %s complete recipe distinfo files\n' "$count"
