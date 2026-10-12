#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real SVG generation and malformed-input checks.
set -eu
[ "$#" = 2 ] || { echo 'Usage: breeze-generators.sh HOST_PREFIX NEW_WORK' >&2; exit 2; }
host=$1
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
ulimit -c 0
mkdir -p "$work/light/actions/16" "$work/dark" "$work/bad/icons/actions/16" "$work/bad/output"
cat > "$work/light/actions/16/ember.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">
<style id="current-color-scheme" type="text/css">.ColorScheme-Text { color: #232629; } .ColorScheme-Background { color: #eff0f1; }</style>
<path class="ColorScheme-Text" fill="currentColor" d="M0 0h16v16H0z"/>
</svg>
SVG
printf '[Icon Theme]\nName=Ember generator test\nDirectories=actions/16\n' > "$work/light/index.theme"
cp "$work/light/actions/16/ember.svg" "$work/original.svg"
"$host/bin/generate-symbolic-dark" "$work/light" "$work/dark" > "$work/dark.log" 2>&1
cmp "$work/original.svg" "$work/light/actions/16/ember.svg"
test -s "$work/dark/actions/16/ember.svg"
grep -q '#fcfcfc' "$work/dark/actions/16/ember.svg"
grep -q '#2a2e32' "$work/dark/actions/16/ember.svg"
ln -s ember.svg "$work/light/actions/16/alias.svg"
"$host/bin/qrcAlias" -o "$work/good.qrc" "$work/light" > "$work/qrc.log" 2>&1
grep -q 'alias="actions/16/alias.svg"' "$work/good.qrc"
printf '<svg><style id="current-color-scheme">broken' > "$work/bad/icons/actions/16/broken.svg"
if "$host/bin/generate-symbolic-dark" "$work/bad/icons" "$work/bad/output" > "$work/bad-dark.log" 2>&1; then
    echo 'FAIL: malformed SVG was reported as a successful conversion' >&2; exit 1
fi
grep -q 'Input XML read errors' "$work/bad-dark.log"
if "$host/bin/qrcAlias" -o "$work/bad.qrc" "$work/bad/icons" > "$work/bad-qrc.log" 2>&1; then
    echo 'FAIL: malformed SVG was included in a successful resource' >&2; exit 1
fi
grep -q 'XML error' "$work/bad-qrc.log"
if grep -E 'ERROR: AddressSanitizer|runtime error:|UndefinedBehaviorSanitizer' "$work/"*.log; then exit 1; fi
echo 'PASS: source SVG preserved, dark colours, resource aliases and malformed XML failures'
