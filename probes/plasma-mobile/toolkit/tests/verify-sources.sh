#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Verify every archive. Apply source patches only to the declared primary archive.
set -eu
[ "$#" -eq 3 ] || [ "$#" -eq 4 ] ||
    { echo "Usage: $0 TOOLKIT VERIFIED_DISTFILES NEW_WORK [RECIPES]" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
toolkit=$(CDPATH= cd -- "$1" && pwd)
recipes=$(CDPATH= cd -- "${4:-$root/pkgsrc}" && pwd)
distfiles=$(CDPATH= cd -- "$2" && pwd)
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
case "$work:$distfiles" in *[!a-zA-Z0-9_./:-]*) echo 'Use paths without shell metacharacters.' >&2; exit 2 ;; esac
cat > "$work/digest" <<'DIGEST'
#!/bin/sh
set -eu
algorithm=$1
shift
if [ "$#" -eq 0 ]; then
    [ "$algorithm" = SHA1 ] || exit 2
    shasum -a 1 | awk '{ print $1 }'
    exit
fi
for file do
    case "$algorithm" in
        SHA512) hash=$(shasum -a 512 "$file" | awk '{ print $1 }') ;;
        BLAKE2s) hash=$("${OPENSSL:-openssl}" dgst -blake2s256 "$file" | awk '{ print $NF }') ;;
        *) exit 2 ;;
    esac
    printf '%s (%s) = %s\n' "$algorithm" "$file" "$hash"
done
DIGEST
chmod +x "$work/digest"
export DIGEST=$work/digest
verifier=${PKGSRC_CHECKSUM_AWK:-$root/upstream/pkgsrc/mk/checksum/checksum.awk}
mkdir "$work/source"
sh "$toolkit/validate.sh" --sources "$toolkit" "$recipes" > "$work/source-plan.tsv"
while IFS="$(printf '\t')" read -r recipe archive sha url role; do
    case "$recipe" in ''|'#'*) continue ;; esac
    pkg=$recipes/$recipe
    [ "$(shasum -a 256 "$distfiles/$archive" | awk '{ print $1 }')" = "$sha" ]
    (cd "$distfiles" && awk -f "$verifier" -- "$pkg/distinfo" "$archive")
    recorded=$(awk -v name="($archive)" '$1 == "Size" && $2 == name { print $4 }' "$pkg/distinfo")
    [ "$(wc -c < "$distfiles/$archive" | tr -d ' ')" = "$recorded" ]
    required=$(awk '/^SHA1 \(patch-/ { gsub(/[()]/, "", $2); print $2 }' "$pkg/distinfo")
    actual=$(find "$pkg" -type f -name 'patch-*' | wc -l | tr -d ' ')
    expected=$(printf '%s\n' "$required" | awk 'NF { n++ } END { print n+0 }')
    [ "$actual" = "$expected" ] || { echo "Patch manifest differs: $recipe" >&2; exit 1; }
    if [ "$role" = primary ] && [ "$expected" -gt 0 ]; then
        stem=${archive%.tar.*}
        stem=${stem%.zip}
        tree=$work/source/$stem
        mkdir "$tree"
        tar -xf "$distfiles/$archive" --strip-components=1 -C "$tree"
        for name in $required; do
            [ -f "$pkg/patches/$name" ]
            awk -f "$verifier" -- -p "$pkg/distinfo" "$pkg/patches/$name"
            patch -f -N -F 0 -p0 -d "$tree" < "$pkg/patches/$name"
        done
    fi
    printf '%s\t%s\n' "$recipe" "$sha" >> "$work/verified.tsv"
done < "$work/source-plan.tsv"
echo 'PASS: all source archives verified; patches apply only to primary sources'
