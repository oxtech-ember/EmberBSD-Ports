#!/bin/sh
# Export the real tree and compare the export with its sources.
set -eu
[ "$#" -eq 1 ] || { echo "Usage: $0 NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
mkdir "$work/tmp" "$work/bin"
tab=$(printf '\t')
script=$root/scripts/prepare-pkgsrc.sh
tree=$work/export
TMPDIR=$work/tmp sh "$script" "$tree" > "$work/export.log" 2>&1 ||
    { tail -n 20 "$work/export.log" >&2; exit 1; }
[ -z "$(find "$work/tmp" -name 'ember-pkgsrc.*')" ]

# Recipes that an infrastructure patch changes differ from their source.
: > "$work/patched"
while IFS="$tab" read -r method first second third; do
    case "$method" in
        patch|git-apply)
            awk '/^(\+\+\+|---) [ab]\// { sub(/^[ab]\//, "", $2); split($2, part, "/"); print part[1] "/" part[2] }' \
                "$root/$first" >> "$work/patched" ;;
        recipe-patch) printf '%s\n' "$second" >> "$work/patched" ;;
    esac
done < "$root/pkgsrc/export.conf"
sort -u -o "$work/patched" "$work/patched"

compared=0
compare() {
    if grep -qxF "$2" "$work/patched"; then
        [ -f "$tree/$2/Makefile" ]
    else
        # The export copies links as files.
        diff -qr "$1" "$tree/$2" > /dev/null || { diff -qr "$1" "$tree/$2" >&2; exit 1; }
    fi
    compared=$((compared + 1))
}
while IFS="$tab" read -r method first second third; do
    case "$method" in
        recipe) compare "$root/$first" "$second" ;;
        file) cmp "$root/$first" "$tree/$second" ;;
    esac
done < "$root/pkgsrc/export.conf"
for package in "$root"/pkgsrc/*/*; do
    [ -d "$package" ] || continue
    compare "$package" "${package#"$root"/pkgsrc/}"
done
grep -v '^#' "$root/pkgsrc/replaces" | sed '/^$/d' | while read -r recipe; do
    [ -f "$tree/$recipe/Makefile" ]
done
pin=$(git -C "$root" ls-files --stage -- upstream/pkgsrc | awk '{ print $2 }')
grep -Fx "$pin" "$tree/EMBERBSD-PKGSRC-REVISION" > /dev/null
[ ! -e "$tree/EMBERBSD-PKGSRC-CONFIG" ]
if sh "$script" "$tree" > "$work/existing.log" 2>&1; then exit 1; fi
if sh "$script" "$work/profile" common-graphics > "$work/profile.log" 2>&1; then exit 1; fi
[ ! -e "$work/profile" ]

# A failure after the archive is created keeps its status and removes the
# temporary files.
REAL_CP=$(command -v cp); export REAL_CP
cat > "$work/bin/cp" <<'SH'
#!/bin/sh
for arg do
    if [ "$arg" = "${EXPORT_FAIL_SOURCE:-}" ]; then exit 42; fi
done
exec "$REAL_CP" "$@"
SH
chmod +x "$work/bin/cp"
status=0
PATH="$work/bin:$PATH" TMPDIR="$work/tmp" EXPORT_FAIL_SOURCE="$root/pkgsrc/defaults.mk.conf" \
    sh "$script" "$work/failed-export" > "$work/failed-export.log" 2>&1 || status=$?
[ "$status" -eq 42 ]
[ -z "$(find "$work/tmp" -name 'ember-pkgsrc.*')" ]
echo "PASS: $compared exported recipes match their sources; exported files, replaces, revision, argument and failure cleanup checks"
