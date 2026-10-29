#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Fetch does not run bmake for a package
# whose distinfo distfiles are all in DISTDIR with the recorded sizes. A
# missing file or another size still runs the fetch. The fetch is recorded,
# not run, and DISTDIR is a new directory, so nothing is downloaded.
# BMAKE, MAKECONF and PKGSRCDIR select a prepared cross tree as for
# scripts/cross-bulk.sh. PKGPATH has a distinfo.
set -eu
[ "$#" -eq 2 ] || { echo 'Usage: cross-bulk-fetch-present.sh NEW_OUTPUT PKGPATH' >&2; exit 2; }
out=$1 path=$2
: "${BMAKE:?}" "${MAKECONF:?}" "${PKGSRCDIR:?}"
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
[ ! -e "$out" ] || exit 2
[ -f "$PKGSRCDIR/$path/distinfo" ] || { echo "$path has no distinfo" >&2; exit 2; }
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/state" "$out/distfiles"
echo "$path" > "$out/state/order"
cat > "$out/bmake" <<WRAP
#!/bin/sh
case " \$* " in *" fetch "*) echo fetch >> $out/fetches; exit 0 ;; esac
exec "$BMAKE" DISTDIR=$out/distfiles "\$@"
WRAP
chmod +x "$out/bmake"
expect()
{
    : > "$out/fetches"
    BMAKE=$out/bmake sh "$ports/scripts/cross-bulk.sh" fetch "$out/state/order" "$out/state" 2> "$out/err" ||
        { cat "$out/err" >&2; echo "FAIL: fetch with $2" >&2; exit 1; }
    calls=$(($(wc -l < "$out/fetches")))
    [ "$calls" -eq "$1" ] || { echo "FAIL: $calls fetch runs with $2, expected $1" >&2; exit 1; }
}
expect 1 'no distfiles'
awk '$1 == "Size" { sub(/^\(/, "", $2); sub(/\)$/, "", $2); print $2, $4 }' "$PKGSRCDIR/$path/distinfo" |
while read -r file size; do
    mkdir -p "$(dirname "$out/distfiles/$file")"
    dd if=/dev/zero of="$out/distfiles/$file" bs=1 count=0 seek="$size" 2> /dev/null
    echo "$file" > "$out/last"
done
expect 0 'all distfiles present'
last=$(cat "$out/last")
printf x >> "$out/distfiles/$last"
expect 1 'a distfile of another size'
rm "$out/distfiles/$last"
expect 1 'a missing distfile'
echo "PASS: fetch skipped only with every distfile present at its recorded size"
