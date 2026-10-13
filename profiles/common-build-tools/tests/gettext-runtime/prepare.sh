#!/bin/sh
# AI-assisted EmberBSD test packaging. Keep upstream files byte-identical.
set -eu
if [ "$#" -ne 3 ]; then
    echo "usage: $0 CONFIGURED_GETTEXT_SOURCE FCITX_SOURCE NEW_PAYLOAD" >&2
    exit 2
fi
gettext_source=$(cd "$1" && pwd -P)
fcitx_source=$(cd "$2" && pwd -P)
payload=$3
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
sha256_file() {
    if command -v sha256 >/dev/null 2>&1; then sha256 -q "$1"
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}
test ! -e "$payload" && test ! -L "$payload"
# Verify all pinned upstream inputs before creating the payload.
while IFS="$(printf '\t')" read -r owner file expected; do
    case "$owner" in gettext) source_root=$gettext_source;; fcitx) source_root=$fcitx_source;; *) exit 1;; esac
    actual=$(sha256_file "$source_root/$file")
    test "$actual" = "$expected" || { echo "source hash mismatch: $owner/$file" >&2; exit 1; }
done < "$script_dir/upstream-sha256.tsv"
grep '^ARCHIVE_VERSION="1.0"$' "$gettext_source/gettext-tools/tests/init-env" >/dev/null
mkdir "$payload"
payload=$(cd "$payload" && pwd -P)
while IFS="$(printf '\t')" read -r owner file expected; do
    case "$owner" in gettext) source_root=$gettext_source;; fcitx) source_root=$fcitx_source;; esac
    mkdir -p "$payload/$owner/$(dirname "$file")"
    cp "$source_root/$file" "$payload/$owner/$file"
done < "$script_dir/upstream-sha256.tsv"
# This is the original configured upstream file. Selected cases use none of
# its compiler, Go, Java, or locale-helper variables. The runner binds MSG*
# to installed tools and provides target-local source/build directories.
cp "$gettext_source/gettext-tools/tests/init-env" "$payload/gettext/gettext-tools/tests/"
cp "$script_dir/run.sh" "$script_dir/fcitx-shell.sh" "$script_dir/cases.tsv" \
    "$script_dir/upstream-sha256.tsv" "$script_dir/README.md" "$payload/"
{
    cat "$script_dir/upstream-sha256.tsv"
    printf 'generated\tgettext/gettext-tools/tests/init-env\t%s\n' \
        "$(sha256_file "$payload/gettext/gettext-tools/tests/init-env")"
    for file in run.sh fcitx-shell.sh cases.tsv README.md; do
        printf 'runner\t%s\t%s\n' "$file" "$(sha256_file "$payload/$file")"
    done
} > "$payload/payload-sha256.tsv"
echo "Prepared $payload"
