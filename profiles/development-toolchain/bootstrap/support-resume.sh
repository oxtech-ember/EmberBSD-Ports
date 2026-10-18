#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Freeze and check failed external support.
set -eu
fail() { echo "$*" >&2; exit 2; }
[ "$#" -ge 2 ] || fail 'Usage: support-resume.sh checkpoint WORK FAILURE_EXIT | check WORK | resume WORK'
action=$1
work=$(CDPATH= cd -- "$2" && pwd -P) || fail 'Missing support work.'
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
parent=$work/support-parent
field() {
    [ "$(grep -c "^$1=" "$2")" -eq 1 ] || fail "Missing or duplicate input: $1"
    sed -n "s/^$1=//p" "$2"
}
hashes() { awk 'length($1) == 64 && $1 !~ /[^0-9a-f]/ && NF == 2 { print }' "$1"; }
map_helpers() {
    awk -v original="$here/" -v frozen="$parent/helpers/" -v identity="$work/external-compiler.txt" -v prior="$parent/external-compiler.txt" '
        length($1) == 64 && $1 !~ /[^0-9a-f]/ && NF == 2 && index($2, original) == 1 {
            sub(original, frozen, $2); print $1 "  " $2; next
        }
        length($1) == 64 && $1 !~ /[^0-9a-f]/ && NF == 2 && $2 == identity {
            print $1 "  " prior; next
        } { print }' "$1"
}
phase_guard() {
    [ -d "$work/src" ] && [ -d "$work/build/gcc" ] && [ -d "$work/stage" ] || fail 'Incomplete external support work.'
    [ ! -L "$work/src" ] && [ ! -L "$work/build" ] && [ ! -L "$work/stage" ] || fail 'Symlink in support work.'
    [ ! -e "$work/build-success" ] && [ ! -L "$work/build-success" ] || fail 'Completed work cannot resume support.'
    [ ! -e "$work/external-runtime-plan.txt" ] && [ ! -L "$work/external-runtime-plan.txt" ] || fail 'Target runtime phase already started.'
    [ -z "$(find "$work/stage" -type f -o -type l)" ] || fail 'Target stage is not empty.'
    triplet=$(field triplet "$work/inputs.txt")
    if [ -d "$work/build/$triplet" ]; then
        [ -z "$(find "$work/build/$triplet" -type f -o -type l)" ] || fail 'Target library objects already exist.'
    fi
    for frontend in cc1 cc1plus; do
        [ ! -e "$work/build/gcc/$frontend" ] && [ ! -L "$work/build/gcc/$frontend" ] || fail 'Language frontend exists in support work.'
    done
    [ "$(field scope "$work/inputs.txt")" = runtime-only-external-compiler ] || fail 'External support scope required.'
}
manifest() {
    tree=$1 tag=$2 output=$3
    [ -z "$(find "$tree" ! -type d ! -type f ! -type l -print)" ] || fail 'Special file in support checkpoint tree.'
    (cd "$tree" && find . -print | LC_ALL=C sort) > "$output/$tag.inventory"
    (cd "$tree" && find . -type f -exec shasum -a 256 {} + | LC_ALL=C sort) > "$output/$tag.sha256"
    (cd "$tree" && find . -type l -exec sh -c 'for entry do printf "%s\t%s\n" "$entry" "$(readlink "$entry")"; done' sh {} + | LC_ALL=C sort) > "$output/$tag.symlinks"
}
record_receipt() {
    cmp "$work/inputs.txt" "$parent/inputs.txt" || fail 'Original receipt changed.'
    map_helpers "$parent/inputs.txt" | sed 's/^scope=runtime-only-external-compiler$/scope=runtime-only-external-support-resume/' > "$work/inputs.txt.next"
    printf 'resume_support_prior_inputs_sha256=%s\n' "$(shasum -a 256 "$parent/inputs.txt" | awk '{print $1}')" >> "$work/inputs.txt.next"
    cat "$work/support-parent.sha256" >> "$work/inputs.txt.next"
    shasum -a 256 "$work/support-parent.sha256" >> "$work/inputs.txt.next"
    mv "$work/inputs.txt.next" "$work/inputs.txt"
}
case "$action" in
checkpoint)
    [ "$#" -eq 3 ] || fail 'Checkpoint requires the actual parent failure exit file.'
    phase_guard
    [ ! -e "$parent" ] && [ ! -L "$parent" ] || fail 'Support checkpoint already exists.'
    failure=$(cat "$3")
    case "$failure" in ''|[!1-9]*|*[!0-9]*) fail 'A nonzero parent failure exit is required.';; esac
    [ -f "$work/support-build.log" ] || fail 'Missing failed support log.'
    hashes "$work/inputs.txt" | shasum -a 256 -c --status || fail 'Original inputs changed before checkpoint.'
    mkdir "$parent" "$parent/helpers"
    cp "$work/inputs.txt" "$parent/inputs.txt"
    cp "$work/external-compiler.txt" "$parent/external-compiler.txt"
    cp "$3" "$parent/failure-exit.txt"
    for log in support-build.log support-host.log configure.log patch.log; do cp "$work/$log" "$parent/$log"; done
    hashes "$parent/inputs.txt" | while read -r digest filename; do
        case "$filename" in "$here/"*.sh) cp "$filename" "$parent/helpers/";; esac
    done
    printf '%s\n' "$here" > "$parent/helper-prefix.txt"
    printf 'failed-external-support\n' > "$parent/phase"
    cp "$here/support-resume.sh" "$parent/checkpoint-producer.sh"
    shasum -a 256 "$parent/checkpoint-producer.sh" > "$parent/checkpoint-producer.sha256"
    find "$parent/helpers" -type f -exec shasum -a 256 {} + | LC_ALL=C sort > "$parent/helpers.sha256"
    manifest "$work/src" source "$parent"
    manifest "$work/build" build "$parent"
    manifest "$(field sysroot "$parent/inputs.txt")" seed "$parent"
    find "$parent" -maxdepth 1 -type f -exec shasum -a 256 {} + | LC_ALL=C sort > "$work/support-parent.sha256"
    echo 'PASS: failed support checkpoint recorded before helper changes';;
check|resume)
    [ "$#" -eq 2 ] || fail 'Unexpected check arguments.'
    phase_guard
    [ -d "$parent" ] && [ ! -L "$parent" ] || fail 'Missing support checkpoint.'
    shasum -a 256 -c --status "$work/support-parent.sha256" "$parent/helpers.sha256" || fail 'Support checkpoint changed.'
    cmp "$work/inputs.txt" "$parent/inputs.txt" || fail 'Original receipt changed.'
    cmp "$work/external-compiler.txt" "$parent/external-compiler.txt" || fail 'Original compiler identity changed.'
    [ "$(cat "$parent/helper-prefix.txt")" = "$here" ] || fail 'Support helper prefix changed.'
    [ "$(cat "$parent/phase")" = failed-external-support ] || fail 'Wrong parent failure phase.'
    map_helpers "$parent/inputs.txt" | hashes /dev/stdin | shasum -a 256 -c --status || fail 'Original source, compiler, seed or tools changed.'
    temporary=$(mktemp -d "$parent/check.XXXXXX")
    trap 'rm -rf "$temporary"' EXIT HUP INT TERM
    manifest "$work/src" source "$temporary"
    manifest "$work/build" build "$temporary"
    manifest "$(field sysroot "$parent/inputs.txt")" seed "$temporary"
    for tag in source build seed; do
        for kind in inventory sha256 symlinks; do
            cmp "$parent/$tag.$kind" "$temporary/$tag.$kind" || fail "Support checkpoint tree changed: $tag/$kind"
        done
    done
    echo 'PASS: unchanged failed support, source and seed trees'
    [ "$action" != resume ] || record_receipt;;
*) fail 'Unknown support resume action.';;
esac
