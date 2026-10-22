#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-pkgsrc-test.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
mkdir "$work/existing" "$work/bin"
printf preserve > "$work/existing/sentinel"
if sh "$root/scripts/prepare-pkgsrc.sh" "$work/existing"; then exit 1; fi
[ "$(cat "$work/existing/sentinel")" = preserve ]
if sh "$root/scripts/prepare-pkgsrc.sh" relative-path; then exit 1; fi
cat > "$work/bin/git" <<'STUB'
#!/bin/sh
case "$*" in
    *ls-files*) printf '160000 1111111111111111111111111111111111111111 0\tupstream/pkgsrc\n' ;;
    *rev-parse*)
        if [ "${FAKE_MATCH:-0}" = 1 ]; then
            printf '1111111111111111111111111111111111111111\n'
        else
            printf '2222222222222222222222222222222222222222\n'
        fi ;;
    *archive*)
        for arg do
            case "$arg" in --output=*) output=${arg#--output=} ;; esac
        done
        tar -cf "$output" -C "$FAKE_ARCHIVE" . ;;
    *) exit 99 ;;
esac
STUB
chmod +x "$work/bin/git"
if PATH="$work/bin:$PATH" sh "$root/scripts/prepare-pkgsrc.sh" "$work/mismatch"; then exit 1; fi
[ ! -e "$work/mismatch" ]
mkdir "$work/upstream"
FAKE_MATCH=1 FAKE_ARCHIVE="$work/upstream" PATH="$work/bin:$PATH" \
    sh "$root/scripts/prepare-pkgsrc.sh" "$work/combined"
[ -f "$work/combined/local-ai/llama-cpp/Makefile" ]
[ -f "$work/combined/local-robotics/zenoh-pico/Makefile" ]
mkdir -p "$work/upstream/devel" "$work/upstream/www"
FAKE_MATCH=1 FAKE_ARCHIVE="$work/upstream" PATH="$work/bin:$PATH" \
    sh "$root/scripts/prepare-pkgsrc.sh" "$work/electron" electron
[ -f "$work/electron/devel/electron44/Makefile" ]
[ -f "$work/electron/www/blanc/Makefile" ]
grep -F 'CATEGORIES=	www' "$work/electron/www/blanc/Makefile" >/dev/null
grep -F 'BLANC_ELECTRON_PKGDIR=	../../devel/electron44' \
    "$work/electron/www/blanc/Makefile" >/dev/null
mkdir "$work/upstream/local-robotics"
printf upstream > "$work/upstream/local-robotics/sentinel"
if FAKE_MATCH=1 FAKE_ARCHIVE="$work/upstream" PATH="$work/bin:$PATH" \
    sh "$root/scripts/prepare-pkgsrc.sh" "$work/collision"; then exit 1; fi
[ "$(cat "$work/collision/local-robotics/sentinel")" = upstream ]
echo 'PASS: path/revision rejection, overlays, Electron export paths, upstream collision preserved'
